from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import NotRequired, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

def add_spend(existing: float, new: float) -> float:
    """Reducer: Adds the new cost to the existing spend."""
    if existing is None: existing = 0.0
    if new is None: new = 0.0
    return existing + new

def add_itinerary(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer: Appends new activities to the itinerary list."""
    if existing is None: existing = []
    if new is None: new = []
    return existing + new

def add_ids(existing: List[str], new: List[str]) -> List[str]:
    return list(dict.fromkeys((existing or []) + (new or [])))

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    
    selected_city: NotRequired[Optional[str]]
    trip_dates: NotRequired[Optional[str]]
    user_preferences: NotRequired[Dict[str, Any]]
    
    total_budget_pkr: NotRequired[float]
    current_spend_pkr: NotRequired[Annotated[float, add_spend]]
    
    itinerary_items: NotRequired[Annotated[List[Dict[str, Any]], add_itinerary]]
    confirmed_tool_call_ids: NotRequired[Annotated[List[str], add_ids]]
    expense_ids: NotRequired[Annotated[List[str], add_ids]]
