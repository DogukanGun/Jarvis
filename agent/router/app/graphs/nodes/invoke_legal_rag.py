"""Invoke the Legal RAG agent synchronously and return the result."""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..state import RouterGraphState

logger = logging.getLogger(__name__)


def invoke_legal_rag(state: RouterGraphState) -> Dict[str, Any]:
    from app.clients.legal_rag_client import LegalRagClient

    message = state.get("message", "")
    user_id = state.get("user_id", "default")

    client = LegalRagClient()
    try:
        result = client.query(message=message, user_id=user_id)
        client.close()

        if result.get("error"):
            raise RuntimeError(result["error"])

        tools_used = list(state.get("tools_used", []))
        tools_used.append("legal-rag")
        tool_results = dict(state.get("tool_results", {}))
        tool_results["legal_rag"] = {
            "response": result.get("response", ""),
            "citations": result.get("citations", []),
            "task_type": result.get("task_type", ""),
            "graph_paths": result.get("graph_paths", []),
            "tools_used": result.get("tools_used", []),
        }
        return {
            "tool_results": tool_results,
            "tools_used": tools_used,
            "response": result.get("response", ""),
        }

    except Exception as e:
        logger.error("Legal RAG invocation failed: %s", e)
        client.close()
        tools_used = list(state.get("tools_used", []))
        tools_used.append("legal-rag")
        tool_results = dict(state.get("tool_results", {}))
        tool_results["legal_rag"] = {"error": str(e)}
        return {"tool_results": tool_results, "tools_used": tools_used}
