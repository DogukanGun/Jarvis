from __future__ import annotations

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem
from ..metrics import MetricsCollector
from ..prompts.evaluator import EVALUATOR_PROMPT


async def run_evaluator(problem: Problem, cli_path: str | None = None, metrics: MetricsCollector | None = None) -> str:
    """Returns 'accept' or 'reject'."""
    prompt = (
        f"{EVALUATOR_PROMPT}\n\n"
        f"Problem ID: {problem.id}\n"
        f"Title: {problem.title}\n"
        f"Description: {problem.description}\n"
        f"Source: {problem.source_url}"
    )

    result = ""
    last_msg = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            cli_path=cli_path,
        ),
    ):
        last_msg = msg
        if hasattr(msg, "result") and msg.result:
            result = msg.result
    if metrics:
        metrics.record("evaluate", last_msg, problem_id=problem.id)

    decision = result.strip().lower()
    if decision not in ("accept", "reject"):
        # Default to accept if unclear
        decision = "accept"
    print(f"[evaluator] Problem '{problem.id}' -> {decision}")
    return decision
