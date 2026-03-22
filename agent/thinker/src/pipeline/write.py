from __future__ import annotations
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem, ExecutionPlan, TestResults, ComparisonReport
from ..metrics import MetricsCollector
from ..prompts.writer import build_writer_prompt


async def run_writer(
    problem: Problem,
    plan: ExecutionPlan,
    test_results: TestResults,
    comparison: ComparisonReport,
    cli_path: str | None = None,
    figures: dict[str, Path] | None = None,
    out_dir: Path | None = None,
    metrics: MetricsCollector | None = None,
) -> Path:
    steps_text = "\n".join(plan.steps)
    metrics_text = "\n".join(f"  {k}: {v}" for k, v in test_results.metrics.items())
    compared_text = "\n".join(f"- {s}" for s in comparison.compared_systems)
    strengths_text = "\n".join(f"- {s}" for s in comparison.strengths)
    weaknesses_text = "\n".join(f"- {w}" for w in comparison.weaknesses)

    # Convert absolute figure paths to relative markdown paths (relative to the tex file's dir)
    outputs_dir = out_dir if out_dir is not None else Path("outputs")
    figure_md_paths: dict[str, str] | None = None
    if figures:
        figure_md_paths = {}
        for key, fig_path in figures.items():
            try:
                figure_md_paths[key] = str(fig_path.relative_to(outputs_dir))
            except ValueError:
                figure_md_paths[key] = str(fig_path)

    prompt = (
        f"{build_writer_prompt(figure_md_paths)}\n\n"
        f"Problem: {problem.title}\n"
        f"Description: {problem.description}\n\n"
        f"Chosen direction: {plan.chosen_direction}\n"
        f"Tech stack: {', '.join(plan.tech_stack)}\n"
        f"Implementation steps:\n{steps_text}\n\n"
        f"Test results:\n"
        f"  Passed: {test_results.passed}\n"
        f"  Output: {test_results.output[:800]}\n"
        f"Metrics:\n{metrics_text}\n\n"
        f"Compared systems:\n{compared_text}\n\n"
        f"Our approach summary: {comparison.our_approach_summary}\n"
        f"Strengths:\n{strengths_text}\n"
        f"Weaknesses:\n{weaknesses_text}"
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
        metrics.record("write", last_msg, problem_id=problem.id)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "paper_draft.tex"
    else:
        out_path = Path("outputs/paper_draft.tex")
    out_path.write_text(result)
    print(f"[writer] Paper draft saved to {out_path}")
    return out_path
