from typing import TypedDict, Annotated, List, Dict, Any
import operator
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    risk_score: float
    impacted_suppliers: List[dict]
    analysis: str
    report_draft: str
    next_step: str
