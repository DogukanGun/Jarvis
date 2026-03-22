from __future__ import annotations
import json
import re

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem, SubProblem
from ..metrics import MetricsCollector
from ..prompts.decomposer import DECOMPOSER_PROMPT


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_sub_problems(text: str, parent: Problem) -> list[SubProblem]:
    raw = _extract_json(text)
    data = json.loads(raw)
    sub_problems = []
    for item in data:
        item["parent_id"] = parent.id
        if "id" not in item or not item["id"]:
            item["id"] = f"{parent.id}-{item.get('research_angle', 'unknown')}"
        sub_problems.append(SubProblem(**item))
    return sub_problems


async def run_decomposer(problem: Problem, cli_path: str | None = None, metrics: MetricsCollector | None = None) -> list[SubProblem]:
    prompt = (
        f"{DECOMPOSER_PROMPT}\n\n"
        f"Problem ID: {problem.id}\n"
        f"Title: {problem.title}\n"
        f"Description: {problem.description}"
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
        metrics.record("decompose", last_msg, problem_id=problem.id)

    sub_problems = _parse_sub_problems(result, problem)
    print(f"[decomposer] Problem '{problem.id}' -> {len(sub_problems)} sub-problems")
    return sub_problems
