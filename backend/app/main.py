import traceback
import json
import logging
import os
import re
import threading
from pathlib import Path
from uuid import uuid4
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from app.agent.tools import convert_currency, get_current_weather
from app.security.prompt_guard import check_user_message

load_dotenv()
from app.agent.graph import agent_graph

app = FastAPI(title="SafarAI Agent Backend", version="1.0.0")
logger = logging.getLogger(__name__)
_expense_locks: dict[str, threading.Lock] = {}
_expense_locks_guard = threading.Lock()


def _expense_lock(thread_id: str) -> threading.Lock:
    with _expense_locks_guard:
        return _expense_locks.setdefault(thread_id, threading.Lock())

def budget_from_message(message: str) -> Optional[float]:
    """Read an explicit PKR budget from chat without treating prices as budgets."""
    match = re.search(r"\bbudget(?:\s+is|\s*:)?\s*(\d[\d,]*(?:\.\d+)?)\s*PKR\b", message, re.IGNORECASE)
    return float(match.group(1).replace(",", "")) if match else None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: Optional[str] = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    total_budget_pkr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank.")
        return value

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value else value

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    total_budget_pkr: float
    current_spend: float
    remaining_budget: float
    itinerary: List[Dict[str, Any]]

class WeatherRequest(BaseModel):
    location: str = Field(min_length=1, max_length=120)

class CurrencyRequest(BaseModel):
    amount: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)
    from_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    to_currency: str = Field(default="PKR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")

class BudgetRequest(BaseModel):
    total_budget_pkr: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)

class ExpenseRequest(BaseModel):
    expense_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    description: str = Field(min_length=1, max_length=160)
    amount_pkr: float = Field(gt=0, le=100_000_000, allow_inf_nan=False)
    category: str = Field(default="Other", min_length=1, max_length=80)

    @field_validator("description", "category")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Expense text cannot be blank.")
        return value

def _tool_result(result: str) -> Dict[str, Any]:
    payload = json.loads(result)
    if not isinstance(payload, dict):
        raise ValueError("Tool returned an invalid response.")
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload

def _thread_config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}

def _state_snapshot(thread_id: str) -> Dict[str, Any]:
    state = agent_graph.get_state(_thread_config(thread_id)).values
    initialized = bool(state)
    total = float(state.get("total_budget_pkr", 0.0))
    spend = float(state.get("current_spend_pkr", 0.0))
    return {
        "thread_id": thread_id,
        "initialized": initialized,
        "total_budget_pkr": total,
        "current_spend": spend,
        "remaining_budget": total - spend,
        "itinerary": state.get("itinerary_items", []),
    }


def _chat_response_for_state(thread_id: str, response: str) -> ChatResponse:
    snapshot = _state_snapshot(thread_id)
    return ChatResponse(response=response, **{key: value for key, value in snapshot.items() if key != "initialized"})


@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/ready")
def readiness_check():
    required_data = Path(__file__).resolve().parents[2] / "data"
    if not required_data.exists():
        raise HTTPException(status_code=503, detail="Application data is unavailable.")
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=503, detail="AI provider configuration is unavailable.")
    return {"status": "ready"}

@app.post("/api/weather")
def weather_endpoint(request: WeatherRequest):
    try:
        return _tool_result(get_current_weather.invoke({"location": request.location.strip()}))
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/api/currency")
def currency_endpoint(request: CurrencyRequest):
    try:
        return _tool_result(convert_currency.invoke({
            "amount": request.amount,
            "from_currency": request.from_currency.upper(),
            "to_currency": request.to_currency.upper(),
        }))
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/api/state/{thread_id}")
def state_endpoint(thread_id: str):
    return _state_snapshot(thread_id.strip())

@app.patch("/api/state/{thread_id}/budget")
def budget_endpoint(thread_id: str, request: BudgetRequest):
    thread_id = thread_id.strip()
    config = _thread_config(thread_id)
    state = agent_graph.get_state(config).values
    if not state:
        agent_graph.update_state(config, {
            "total_budget_pkr": request.total_budget_pkr,
            "current_spend_pkr": 0.0,
            "itinerary_items": [],
        })
    else:
        if request.total_budget_pkr < float(state.get("current_spend_pkr", 0.0)):
            raise HTTPException(status_code=409, detail="Budget cannot be lower than current spending.")
        agent_graph.update_state(config, {"total_budget_pkr": request.total_budget_pkr})
    return _state_snapshot(thread_id)

@app.post("/api/state/{thread_id}/expenses")
def expense_endpoint(thread_id: str, request: ExpenseRequest):
    thread_id = thread_id.strip()
    with _expense_lock(thread_id):
        config = _thread_config(thread_id)
        state = agent_graph.get_state(config).values
        total = float(state.get("total_budget_pkr", 0.0))
        spent = float(state.get("current_spend_pkr", 0.0))
        if not state:
            raise HTTPException(status_code=409, detail="Set a trip budget before adding an expense.")
        if request.expense_id in state.get("expense_ids", []):
            return _state_snapshot(thread_id)
        if spent + request.amount_pkr > total:
            raise HTTPException(status_code=409, detail="This expense exceeds your remaining budget.")
        agent_graph.update_state(config, {
            "current_spend_pkr": request.amount_pkr,
            "itinerary_items": [{
                "activity": request.description,
                "cost": request.amount_pkr,
                "currency": "PKR",
                "category": request.category,
            }],
            "expense_ids": [request.expense_id],
        })
        return _state_snapshot(thread_id)

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    thread_id = (request.thread_id or str(uuid4())).strip()
    if not thread_id:
        thread_id = str(uuid4())

    try:
        if not request.message.strip():
            raise HTTPException(status_code=422, detail="Message cannot be blank.")

        security_result = check_user_message(request.message)
        if not security_result.allowed:
            logger.warning("chat_guard_rejected thread_id=%s category=%s", thread_id, security_result.reason)
            if security_result.is_prompt_injection:
                refusal = "I can help with travel-related questions, but I can't follow requests to override my instructions or access internal information."
            else:
                refusal = "I'm your AI Travel Assistant, so I can help with travel planning, destinations, restaurants, policies, weather, currency, and budget-related questions."
            return _chat_response_for_state(thread_id, refusal)

        config = _thread_config(thread_id)
        message_budget = budget_from_message(request.message)
        requested_budget = message_budget if message_budget is not None else request.total_budget_pkr
        
        # Check if this thread has memory. If not, initialize the budget.
        current_state = agent_graph.get_state(config)
        if not current_state.values:
            agent_graph.update_state(config, {
                "total_budget_pkr": requested_budget or 0.0,
                "current_spend_pkr": 0.0,
                "itinerary_items": []
            })
        elif message_budget is not None:
            # A widget rerun resends its value; only an explicit chat statement
            # changes an established conversation's budget.
            agent_graph.update_state(config, {"total_budget_pkr": message_budget})

        # Run the agent
        result = agent_graph.invoke({"messages": [HumanMessage(content=request.message.strip())]}, config)
        final_state = agent_graph.get_state(config).values
        
        spend = final_state.get("current_spend_pkr", 0.0)
        remaining = final_state.get("total_budget_pkr", 0.0) - spend
        
        return ChatResponse(
            response=result["messages"][-1].content,
            thread_id=thread_id,
            total_budget_pkr=final_state.get("total_budget_pkr", 0.0),
            current_spend=spend,
            remaining_budget=remaining,
            itinerary=final_state.get("itinerary_items", [])
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("chat_endpoint_failed thread_id=%s", thread_id)
        raise HTTPException(status_code=503, detail="Travel assistant is temporarily unavailable. Please try again shortly.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
