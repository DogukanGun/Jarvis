from __future__ import annotations
import json
import re
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem, SubProblemReport, ExecutionPlan
from ..metrics import MetricsCollector
from ..prompts.planner import PLANNER_PROMPT


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_plan(text: str, problem_id: str) -> ExecutionPlan:
    if text:
        raw = _extract_json(text)
        try:
            data = json.loads(raw)
            return ExecutionPlan(**data)
        except Exception:
            pass
        match = re.search(r'\{.*?"chosen_direction".*?\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return ExecutionPlan(**data)
            except Exception:
                pass
    return ExecutionPlan(
        problem_id=problem_id,
        chosen_direction="Unable to parse plan. Manual review needed.",
        steps=[],
        tech_stack=[],
        validation_criteria=[],
    )


async def run_planner(
    problem: Problem, reports: list[SubProblemReport], cli_path: str | None = None,
    out_dir: Path | None = None, metrics: MetricsCollector | None = None,
) -> ExecutionPlan:
    reports_text = "\n\n".join(
        f"Sub-problem {r.sub_problem_id}:\nFindings: {r.findings}\nPlan: {r.implementation_plan}"
        for r in reports
    )

    prompt = (
        f"{PLANNER_PROMPT}\n\n"
        f"Problem ID: {problem.id}\n"
        f"Title: {problem.title}\n"
        f"Description: {problem.description}\n\n"
        f"Sub-agent research reports:\n{reports_text}"
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
        metrics.record("plan", last_msg, problem_id=problem.id)

    plan = _parse_plan(result, problem.id)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "execution_plan.json"
    else:
        fallback = Path("outputs/execution_plans")
        fallback.mkdir(parents=True, exist_ok=True)
        out_path = fallback / f"{problem.id}.json"
    out_path.write_text(json.dumps(plan.model_dump(), indent=2))
    print(f"[planner] Saved execution plan for '{problem.id}' to {out_path}")
    return plan
