from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    user_id: str = "default"
    message: str
    target_tools: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None


class ExecuteResponse(BaseModel):
    response: str
    report: Dict[str, Any] = {}
    tools_used: List[str] = []
    findings: List[Dict[str, Any]] = []
    job_ids: List[str] = []
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    job_id: Optional[str] = None


class AsyncExecuteResponse(BaseModel):
    job_id: str
    status: str = "started"
    message: str = ""


class ConfirmRequest(BaseModel):
    confirmed: bool


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    tool_name: str = ""
    started_at: str = ""
    result: Optional[Dict[str, Any]] = None


class CommandRequest(BaseModel):
    command: str


class CommandResponse(BaseModel):
    output: str
    success: bool


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    total: int
