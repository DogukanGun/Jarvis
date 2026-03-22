from __future__ import annotations
import json
import re
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem, SubProblemReport, TestResults, ComparisonReport
from ..metrics import MetricsCollector
from ..prompts.comparator import COMPARATOR_PROMPT


def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_comparison(text: str, problem_id: str) -> ComparisonReport:
    if text:
        raw = _extract_json(text)
        try:
            data = json.loads(raw)
            return ComparisonReport(**data)
        except Exception:
            pass
        match = re.search(r'\{.*?"our_approach_summary".*?\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return ComparisonReport(**data)
            except Exception:
                pass
    return ComparisonReport(
        problem_id=problem_id,
        our_approach_summary=text[:1000] if text else "No comparison output.",
        compared_systems=[],
        strengths=[],
        weaknesses=[],
    )


async def run_comparator(
    problem: Problem,
    test_results: TestResults,
    reports: list[SubProblemReport],
    cli_path: str | None = None,
    out_dir: Path | None = None,
    metrics: MetricsCollector | None = None,
) -> ComparisonReport:
    baseline_report = next(
        (r for r in reports if "baselines" in r.sub_problem_id), None
    )
    baseline_text = baseline_report.findings if baseline_report else "No baseline report available."

    prompt = (
        f"{COMPARATOR_PROMPT}\n\n"
        f"Problem ID: {problem.id}\n"
        f"Title: {problem.title}\n"
        f"Description: {problem.description}\n\n"
        f"Our test results:\n"
        f"  Passed: {test_results.passed}\n"
        f"  Output: {test_results.output[:500]}\n"
        f"  Metrics: {test_results.metrics}\n\n"
        f"Baseline research findings:\n{baseline_text}"
    )

    result = ""
    last_msg = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["WebSearch"],
            cli_path=cli_path,
        ),
    ):
        last_msg = msg
        if hasattr(msg, "result") and msg.result:
            result = msg.result
    if metrics:
        metrics.record("compare", last_msg, problem_id=problem.id)

    comparison = _parse_comparison(result, problem.id)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "comparison_report.md"
    else:
        out_path = Path("outputs/comparison_report.md")
    md = f"# Comparison Report: {problem.id}\n\n"
    md += f"## Our Approach\n{comparison.our_approach_summary}\n\n"
    md += "## Compared Systems\n" + "\n".join(f"- {s}" for s in comparison.compared_systems) + "\n\n"
    md += "## Strengths\n" + "\n".join(f"- {s}" for s in comparison.strengths) + "\n\n"
    md += "## Weaknesses\n" + "\n".join(f"- {w}" for w in comparison.weaknesses) + "\n"
    out_path.write_text(md)
    print(f"[comparator] Saved comparison report to {out_path}")
    return comparison
