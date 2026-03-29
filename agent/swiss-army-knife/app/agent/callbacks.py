"""LangChain callback handler that broadcasts agent progress via SSE.

Attach an instance of ``AgentProgressCallbackHandler`` to AgentExecutor so
every tool call, LLM reasoning step, and final answer is pushed to the
monitor's SSE stream in real-time instead of only appearing after the whole
job completes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class AgentProgressCallbackHandler(BaseCallbackHandler):
    """Pushes granular agent progress events to the SSE broadcast stream.

    Every event carries the ``job_id`` so the monitor dashboard can group
    events by job and display them in the correct panel.
    """

    def __init__(self, job_id: str) -> None:
        super().__init__()
        self.job_id = job_id
        # Track the current tool name across on_tool_start / on_tool_end
        self._current_tool: str = ""

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **payload: Any) -> None:
        """Broadcast an event; silently swallows errors so the agent keeps running."""
        try:
            from app.server import broadcast_event  # lazy import to avoid circular

            broadcast_event({"type": event_type, "job_id": self.job_id, **payload})
        except Exception as exc:
            logger.debug("broadcast_event failed in callback (%s): %s", event_type, exc)

    # ------------------------------------------------------------------
    # Tool lifecycle
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        tool_name: str = serialized.get("name", "unknown_tool")
        self._current_tool = tool_name
        self._emit(
            "tool_start",
            tool=tool_name,
            input=str(input_str)[:500],
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        output_str = str(output)
        self._emit(
            "tool_end",
            tool=self._current_tool,
            output=output_str[:1000],
            truncated=len(output_str) > 1000,
        )

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._emit(
            "tool_error",
            tool=self._current_tool,
            error=str(error)[:500],
        )

    # ------------------------------------------------------------------
    # Agent reasoning / flow
    # ------------------------------------------------------------------

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        log_snippet = (action.log or "").strip()[:500]
        self._emit(
            "agent_thinking",
            tool=action.tool,
            tool_input=str(action.tool_input)[:300],
            log=log_snippet,
        )

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        output = finish.return_values.get("output", "")
        self._emit(
            "agent_done",
            output=str(output)[:1000],
        )

    # ------------------------------------------------------------------
    # LLM lifecycle (lightweight — just signal that the LLM is thinking)
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._emit("llm_start", model=serialized.get("name", "llm"))

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._emit("llm_end")

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        self._emit("llm_error", error=str(error)[:300])
