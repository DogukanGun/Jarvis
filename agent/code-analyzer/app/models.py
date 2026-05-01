from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    user_id: str = "default"
    message: str
    target_tools: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    confirmed: bool = False


class ExecuteResponse(BaseModel):
    response: str
    report: Dict[str, Any] = {}
    tools_used: List[str] = []
    findings: List[Dict[str, Any]] = []
    job_ids: List[str] = []
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    job_id: Optional[str] = None


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    total: int
