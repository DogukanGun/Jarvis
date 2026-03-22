"""Swiss Army Knife graph state definition."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class SwissArmyKnifeState(TypedDict, total=False):
    # Input
    user_id: str
    message: str

    # Planning
    plan: Dict[str, Any]
    selected_tools: List[Dict[str, Any]]

    # Confirmation
    requires_confirmation: bool
    confirmation_prompt: str
    confirmed: bool

    # Execution loop
    current_tool_index: int
    tool_results: List[Dict[str, Any]]
    tools_used: List[str]

    # Interpretation
    findings: List[Dict[str, Any]]
    needs_more_tools: bool

    # Output
    report: Dict[str, Any]
    response: str
    error: Optional[str]
    job_id: Optional[str]
