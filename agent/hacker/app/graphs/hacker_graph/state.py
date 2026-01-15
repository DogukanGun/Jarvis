from typing import TypedDict, Optional, List, Dict, Any, Literal


class ToolResult(TypedDict):
    """Result from executing a CLI command."""
    cmd: str
    exit_code: int
    stdout: str
    stderr: str


class HackerGraphState(TypedDict, total=False):
    """
    State for the Hacker Agent LangGraph.

    Organized by the node that produces each field.
    """
    # ===== INPUT =====
    user_id: str
    conversation: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]

    # ===== PLANNER OUTPUT =====
    decision_text: str  # Natural language decision from planner
    planner_action: Literal["DONE", "CALL_TOOL"]  # Action type
    final_answer: Optional[str]  # Final answer when DONE

    # ===== COMPILER OUTPUT =====
    tool_request: Optional[Dict[str, Any]]  # {"action": "CALL_TOOL", "tool": "run_cli", "args": {"cmd": "..."}}
    compiler_action: Literal["run_cli", "finish", "error"]  # Which tool compiler called
    compiler_error: Optional[str]  # Error from compiler if any
    compiler_retry_count: int  # Number of compiler retries

    # ===== VALIDATOR OUTPUT =====
    is_valid: bool  # Whether tool_request passed validation
    validation_errors: List[str]  # List of validation error messages

    # ===== EXECUTOR OUTPUT =====
    last_tool_result: Optional[ToolResult]  # Most recent tool execution result

    # ===== CONTROL =====
    step_count: int  # Current step number
    max_steps: int  # Maximum allowed steps
    tool_history: List[ToolResult]  # History of all tool executions
    errors: List[str]  # Accumulated errors throughout execution
