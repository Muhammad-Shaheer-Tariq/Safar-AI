import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    get_current_weather, convert_currency, search_travel_policies,
    find_restaurants, find_attractions, add_to_itinerary, export_itinerary_email
)

tools = [
    get_current_weather, convert_currency, search_travel_policies,
    find_restaurants, find_attractions, add_to_itinerary, export_itinerary_email
]
llm_with_tools = None


def get_llm_with_tools():
    """Create the Groq client only when a chat request needs it."""
    global llm_with_tools
    if llm_with_tools is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, api_key=api_key)
        llm_with_tools = llm.bind_tools(tools)
    return llm_with_tools

def travel_consultant_node(state: AgentState) -> dict:
    messages = state["messages"]
    
    # Inject Live Budget into LLM
    remaining = state.get("total_budget_pkr", 0.0) - state.get("current_spend_pkr", 0.0)
    budget_context = f"\n\n[LIVE STATE] Budget: {state.get('total_budget_pkr')} PKR | Spend: {state.get('current_spend_pkr')} PKR | Remaining: {remaining} PKR"
    
    if not isinstance(messages[0], SystemMessage):
        full_context = [SystemMessage(content=SYSTEM_PROMPT + budget_context)] + messages
    else:
        full_context = [SystemMessage(content=SYSTEM_PROMPT + budget_context)] + messages[1:]
        
    response = get_llm_with_tools().invoke(full_context)
    state_updates = {"messages": [response]}
    
    return state_updates


def apply_confirmed_itinerary(state: AgentState) -> dict:
    """Charge only successful, unprocessed itinerary tool calls."""
    processed_ids = set(state.get("confirmed_tool_call_ids", []))
    updates = {"confirmed_tool_call_ids": []}
    current_spend = state.get("current_spend_pkr", 0.0)
    total_budget = state.get("total_budget_pkr", 0.0)

    for message in state["messages"]:
        if not isinstance(message, ToolMessage) or message.name != "add_to_itinerary":
            continue
        if message.tool_call_id in processed_ids or getattr(message, "status", "success") == "error":
            continue
        try:
            item = json.loads(message.content)
            cost = float(item["cost_pkr"])
            if item.get("status") != "confirmed" or item.get("currency") != "PKR" or cost <= 0:
                continue
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            continue

        updates["confirmed_tool_call_ids"].append(message.tool_call_id)
        if current_spend + cost > total_budget:
            updates.setdefault("messages", []).append(ToolMessage(
                content=(f"Not added: {item['activity']} costs {cost:,.2f} PKR, which exceeds "
                         f"the remaining budget of {total_budget - current_spend:,.2f} PKR."),
                tool_call_id=message.tool_call_id,
                id=message.id,
                name="add_to_itinerary",
            ))
            continue

        updates["current_spend_pkr"] = updates.get("current_spend_pkr", 0.0) + cost
        updates.setdefault("itinerary_items", []).append({
            "activity": item["activity"], "cost": cost, "currency": "PKR", "category": item["category"],
        })
        current_spend += cost

    return updates

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("consultant", travel_consultant_node)
    workflow.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    workflow.add_node("apply_itinerary", apply_confirmed_itinerary)
    
    workflow.add_edge(START, "consultant")
    workflow.add_conditional_edges("consultant", tools_condition)
    workflow.add_edge("tools", "apply_itinerary")
    workflow.add_edge("apply_itinerary", "consultant")
    
    return workflow.compile(checkpointer=memory)

memory = MemorySaver()
agent_graph = build_graph()
