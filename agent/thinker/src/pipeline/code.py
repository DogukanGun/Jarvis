from __future__ import annotations
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import ExecutionPlan
from ..metrics import MetricsCollector
from ..prompts.coder import CODER_PROMPT


async def run_coder(plan: ExecutionPlan, cli_path: str | None = None, out_dir: Path | None = None, metrics: MetricsCollector | None = None) -> Path:
    if out_dir is not None:
        code_dir = out_dir / "code"
    else:
        code_dir = Path(f"outputs/code/{plan.problem_id}")
    code_dir.mkdir(parents=True, exist_ok=True)

    steps_text = "\n".join(plan.steps)
    tech_text = ", ".join(plan.tech_stack)
    criteria_text = "\n".join(f"- {c}" for c in plan.validation_criteria)

    prompt = (
        f"{CODER_PROMPT}\n\n"
        f"Problem ID: {plan.problem_id}\n"
        f"Direction: {plan.chosen_direction}\n\n"
        f"Tech stack: {tech_text}\n\n"
        f"Implementation steps:\n{steps_text}\n\n"
        f"Validation criteria:\n{criteria_text}\n\n"
        f"Write all code to: {code_dir}/"
    )

    last_msg = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Write", "Edit", "Bash", "Read"],
            cli_path=cli_path,
        ),
    ):
        last_msg = msg
    if metrics:
        metrics.record("code", last_msg, problem_id=plan.problem_id)

    print(f"[coder] Code written to {code_dir}")
    return code_dir
