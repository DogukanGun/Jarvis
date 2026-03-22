from __future__ import annotations
import json
import re
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import ExecutionPlan, TestResults
from ..metrics import MetricsCollector
from ..prompts.tester import TESTER_PROMPT


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_results(text: str, problem_id: str) -> TestResults:
    if text:
        raw = _extract_json(text)
        # Try direct parse
        try:
            data = json.loads(raw)
            return TestResults(**data)
        except Exception:
            pass
        # Try to find a JSON object in the text
        match = re.search(r'\{.*?"passed".*?\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return TestResults(**data)
            except Exception:
                pass
    # Fallback: treat raw output as the test output
    return TestResults(
        problem_id=problem_id,
        passed=False,
        output=text[:2000] if text else "No output from tester agent.",
        metrics={},
    )


async def run_tester(plan: ExecutionPlan, code_dir: Path, cli_path: str | None = None, out_dir: Path | None = None, metrics: MetricsCollector | None = None) -> TestResults:
    criteria_text = "\n".join(f"- {c}" for c in plan.validation_criteria)

    prompt = (
        f"{TESTER_PROMPT}\n\n"
        f"Problem ID: {plan.problem_id}\n"
        f"Code directory: {code_dir}\n\n"
        f"Validation criteria to check:\n{criteria_text}"
    )

    result = ""
    last_msg = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Read"],
            cli_path=cli_path,
            output_format={
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "problem_id": {"type": "string"},
                        "passed": {"type": "boolean"},
                        "output": {"type": "string"},
                        "metrics": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "required": ["problem_id", "passed", "output", "metrics"],
                },
            },
        ),
    ):
        last_msg = msg
        if hasattr(msg, "result") and msg.result:
            result = msg.result
    if metrics:
        metrics.record("test", last_msg, problem_id=plan.problem_id)

    test_results = _parse_results(result, plan.problem_id)

    out_path = Path("outputs/test_results.json")
    # Append or create
    existing = []
    if out_path.exists():
        existing = json.loads(out_path.read_text())
    existing.append(test_results.model_dump())
    out_path.write_text(json.dumps(existing, indent=2))
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        per_problem_path = out_dir / "test_results.json"
        per_problem_path.write_text(json.dumps(test_results.model_dump(), indent=2))
    print(f"[tester] Problem '{plan.problem_id}': passed={test_results.passed}")
    return test_results
