"""Thin compatibility shim — delegates to the LangChain agent runner.

The old LangGraph StateGraph has been replaced by a proper LangChain
AgentExecutor in ``app/agent/runner``.  This module preserves the
``run_tool_graph`` function signature so that ``server.py`` and
``kafka/consumer.py`` require no changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.agent.runner import run_agent

logger = logging.getLogger(__name__)


async def run_tool_graph(
    user_id: str,
    message: str,
    target_tools: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    confirmed: bool = False,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the LangChain agent and return the final result dict.

    Drop-in replacement for the former LangGraph ``run_tool_graph``.
    All arguments and the returned dict shape are identical.
    """
    return await run_agent(
        user_id=user_id,
        message=message,
        target_tools=target_tools,
        parameters=parameters,
        confirmed=confirmed,
        job_id=job_id,
    )
