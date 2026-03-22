"""
Problem-to-Paper: Main orchestrator.

Usage:
    python -m src.main
    python -m src.main --topic "LLM efficiency and compression"
"""
from __future__ import annotations
import asyncio
import argparse
import sys
from pathlib import Path

import shutil
import os
from dotenv import load_dotenv

# Load .env first so any other dotenv consumers get the vars
load_dotenv()

# Unset vars that block or misdirect claude CLI subprocesses.
# Must happen AFTER load_dotenv() since dotenv would re-add them.
os.environ.pop("CLAUDECODE", None)
os.environ.pop("CLAUDE_CODE_ENTRYPOINT", None)
# Don't pass ANTHROPIC_API_KEY to the claude subprocess — it would try to use
# the direct API (which needs billing credits). Instead let the subprocess use
# the stored Claude Code auth (which is already authenticated and working).
os.environ.pop("ANTHROPIC_API_KEY", None)

from .metrics import MetricsCollector
from .monitor import PipelineMonitor
from .healer import (
    Healer,
    validate_gather, validate_evaluate, validate_decompose,
    validate_research, validate_plan, validate_code,
    validate_test, validate_compare, validate_write, validate_pdf,
)
from .pipeline.gather import run_gatherer
from .pipeline.evaluate import run_evaluator
from .pipeline.decompose import run_decomposer
from .pipeline.research import run_research_swarm
from .pipeline.plan import run_planner
from .pipeline.code import run_coder
from .pipeline.test import run_tester
from .pipeline.compare import run_comparator
from .pipeline.write import run_writer
from .pipeline.visualize import run_visualizer
from .pipeline.pdf import run_pdf_converter


AGENT_CLI = {
    "qwen": shutil.which("qwen"),
    "claude": shutil.which("claude"),
}


async def main(
    seed_topic: str = "LLM efficiency and compression",
    max_problems: int | None = None,
    max_accepted: int | None = None,
    max_research: int | None = None,
    agent: str = "qwen",
) -> None:
    cli_path = AGENT_CLI.get(agent)
    if cli_path is None:
        print(f"Error: CLI for agent '{agent}' not found on PATH. Exiting.")
        sys.exit(1)

    collector = MetricsCollector(topic=seed_topic)
    healer = Healer(cli_path=cli_path, lessons_path=Path("outputs/lessons_learned.json"), metrics=collector)

    # Try to connect to existing monitor server, or start a new one
    monitor = PipelineMonitor(port=8585)
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8585/api/health", timeout=2)
        # Server already running — use a remote emitter
        print("[monitor] Connecting to existing monitor server at :8585")
        monitor._remote_mode = True
    except Exception:
        await monitor.start()
        monitor._remote_mode = False

    print(f"\n{'='*60}")
    print(f"Problem-to-Paper Pipeline")
    print(f"Seed topic: {seed_topic}")
    print(f"Agent: {agent} ({cli_path})")
    print(f"Lessons loaded: {len(healer.lessons)}")
    print(f"Monitor: http://localhost:8585")
    print(f"Dashboard: http://localhost:3000")
    print(f"{'='*60}\n")

    monitor.emit("pipeline_start", {"topic": seed_topic, "agent": agent})

    # Phase 1: Gather candidate problems
    print("[Phase 1] Gathering problems...")
    monitor.emit("phase_start", {"phase": "gather"})
    try:
        problems = await run_gatherer(seed_topic, cli_path=cli_path, metrics=collector)
        err = validate_gather(problems)
        if err:
            monitor.emit("phase_error", {"phase": "gather", "error": err})
            await healer.heal("gather", err, context=f"Topic: {seed_topic}")
        else:
            monitor.emit("phase_end", {"phase": "gather", "result": f"{len(problems)} problems"})
    except Exception as e:
        monitor.emit("phase_error", {"phase": "gather", "error": str(e)})
        await healer.heal("gather", f"Phase crashed: {e}", context=f"Topic: {seed_topic}")
        problems = []
    print(f"  Found {len(problems)} problems.\n")

    # Phase 2: Evaluate viability
    print("[Phase 2] Evaluating viability...")
    eval_tasks = problems[:max_problems] if max_problems is not None else problems
    if max_problems is not None:
        print(f"  Limiting to {len(eval_tasks)}/{len(problems)} problems (--max-problems {max_problems})\n")
    accepted = []
    for p in eval_tasks:
        monitor.emit("phase_start", {"phase": "evaluate", "problem_id": p.id})
        try:
            decision = await run_evaluator(p, cli_path=cli_path, metrics=collector)
            err = validate_evaluate(decision, p.id)
            if err:
                monitor.emit("phase_error", {"phase": "evaluate", "problem_id": p.id, "error": err})
                await healer.heal("evaluate", err, context=f"Problem: {p.id}")
            else:
                monitor.emit("phase_end", {"phase": "evaluate", "problem_id": p.id, "result": decision})
            if decision == "accept":
                accepted.append(p)
        except Exception as e:
            monitor.emit("phase_error", {"phase": "evaluate", "problem_id": p.id, "error": str(e)})
            await healer.heal("evaluate", f"Phase crashed: {e}", context=f"Problem: {p.id}")
    print(f"  Accepted {len(accepted)}/{len(eval_tasks)} problems.\n")

    if not accepted:
        print("No problems accepted. Exiting.")
        sys.exit(1)

    # Phase 3: Decompose problems into sub-problems
    print("[Phase 3] Decomposing problems...")
    decompose_tasks = accepted[:max_accepted] if max_accepted is not None else accepted
    if max_accepted is not None:
        print(f"  Limiting to {len(decompose_tasks)}/{len(accepted)} accepted problems (--max-accepted {max_accepted})\n")
    all_sub_problems = []
    for p in decompose_tasks:
        monitor.emit("phase_start", {"phase": "decompose", "problem_id": p.id})
        try:
            sps = await run_decomposer(p, cli_path=cli_path, metrics=collector)
            err = validate_decompose(sps, p.id)
            if err:
                monitor.emit("phase_error", {"phase": "decompose", "problem_id": p.id, "error": err})
                await healer.heal("decompose", err, context=f"Problem: {p.id}")
            else:
                monitor.emit("phase_end", {"phase": "decompose", "problem_id": p.id, "result": f"{len(sps)} sub-problems"})
            all_sub_problems.extend(sps)
        except Exception as e:
            monitor.emit("phase_error", {"phase": "decompose", "problem_id": p.id, "error": str(e)})
            await healer.heal("decompose", f"Phase crashed: {e}", context=f"Problem: {p.id}")
    print(f"  Total sub-problems: {len(all_sub_problems)}\n")

    # Phase 4: Run research swarm
    print("[Phase 4] Running research swarm...")
    research_tasks = all_sub_problems[:max_research] if max_research is not None else all_sub_problems
    if max_research is not None:
        print(f"  Limiting to {len(research_tasks)}/{len(all_sub_problems)} sub-problems (--max-research {max_research})\n")
    monitor.emit("phase_start", {"phase": "research"})
    try:
        all_reports = await run_research_swarm(research_tasks, cli_path=cli_path, metrics=collector)
        err = validate_research(all_reports)
        if err:
            monitor.emit("phase_error", {"phase": "research", "error": err})
            await healer.heal("research", err, context=f"Sub-problems: {len(research_tasks)}")
        else:
            monitor.emit("phase_end", {"phase": "research", "result": f"{len(all_reports)} reports"})
    except Exception as e:
        monitor.emit("phase_error", {"phase": "research", "error": str(e)})
        await healer.heal("research", f"Phase crashed: {e}")
        all_reports = []
    print(f"  Collected {len(all_reports)} sub-agent reports.\n")

    # Phases 5-10: Per accepted problem
    problem_dirs: list[str] = []
    for problem in decompose_tasks:
        problem_dir = Path(f"outputs/{problem.id}")
        problem_dir.mkdir(parents=True, exist_ok=True)
        problem_dirs.append(problem.id)

        print(f"\n{'='*60}")
        print(f"Processing problem: {problem.id}")
        print(f"  Output folder: {problem_dir}/")
        print(f"{'='*60}")

        # Filter reports for this problem
        problem_reports = [
            r for r in all_reports
            if r.sub_problem_id.startswith(problem.id)
        ]

        ctx = f"Problem: {problem.id}"

        # Phase 5: Plan
        print(f"[Phase 5] Planning for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "plan", "problem_id": problem.id})
        try:
            plan = await run_planner(problem, problem_reports, cli_path=cli_path, out_dir=problem_dir, metrics=collector)
            err = validate_plan(plan, problem.id)
            if err:
                monitor.emit("phase_error", {"phase": "plan", "problem_id": problem.id, "error": err})
                await healer.heal("plan", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "plan", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "plan", "problem_id": problem.id, "error": str(e)})
            await healer.heal("plan", f"Phase crashed: {e}", context=ctx)
            continue

        # Phase 6: Code
        print(f"[Phase 6] Coding for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "code", "problem_id": problem.id})
        try:
            code_dir = await run_coder(plan, cli_path=cli_path, out_dir=problem_dir, metrics=collector)
            err = validate_code(code_dir, problem.id)
            if err:
                monitor.emit("phase_error", {"phase": "code", "problem_id": problem.id, "error": err})
                await healer.heal("code", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "code", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "code", "problem_id": problem.id, "error": str(e)})
            await healer.heal("code", f"Phase crashed: {e}", context=ctx)
            code_dir = problem_dir / "code"

        # Phase 7: Test
        print(f"[Phase 7] Testing for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "test", "problem_id": problem.id})
        try:
            test_results = await run_tester(plan, code_dir, cli_path=cli_path, out_dir=problem_dir, metrics=collector)
            err = validate_test(test_results, problem.id)
            if err:
                monitor.emit("phase_error", {"phase": "test", "problem_id": problem.id, "error": err})
                await healer.heal("test", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "test", "problem_id": problem.id, "result": f"passed={test_results.passed}"})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "test", "problem_id": problem.id, "error": str(e)})
            await healer.heal("test", f"Phase crashed: {e}", context=ctx)
            from .models import TestResults
            test_results = TestResults(problem_id=problem.id, passed=False, output=str(e), metrics={})

        # Phase 8: Compare
        print(f"[Phase 8] Comparing for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "compare", "problem_id": problem.id})
        try:
            comparison = await run_comparator(problem, test_results, problem_reports, cli_path=cli_path, out_dir=problem_dir, metrics=collector)
            err = validate_compare(comparison, problem.id)
            if err:
                monitor.emit("phase_error", {"phase": "compare", "problem_id": problem.id, "error": err})
                await healer.heal("compare", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "compare", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "compare", "problem_id": problem.id, "error": str(e)})
            await healer.heal("compare", f"Phase crashed: {e}", context=ctx)
            from .models import ComparisonReport
            comparison = ComparisonReport(problem_id=problem.id, our_approach_summary=str(e), compared_systems=[], strengths=[], weaknesses=[])

        # Phase 8.5: Visualize
        print(f"[Phase 8.5] Generating figures for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "visualize", "problem_id": problem.id})
        try:
            figures = run_visualizer(plan, test_results, comparison, out_dir=problem_dir)
            monitor.emit("phase_end", {"phase": "visualize", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "visualize", "problem_id": problem.id, "error": str(e)})
            await healer.heal("visualize", f"Phase crashed: {e}", context=ctx)
            figures = {}

        # Phase 9: Write paper
        print(f"[Phase 9] Writing paper for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "write", "problem_id": problem.id})
        try:
            paper_path = await run_writer(problem, plan, test_results, comparison, cli_path=cli_path, figures=figures, out_dir=problem_dir, metrics=collector)
            err = validate_write(paper_path)
            if err:
                monitor.emit("phase_error", {"phase": "write", "problem_id": problem.id, "error": err})
                await healer.heal("write", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "write", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "write", "problem_id": problem.id, "error": str(e)})
            await healer.heal("write", f"Phase crashed: {e}", context=ctx)
            paper_path = problem_dir / "paper_draft.tex"

        # Phase 10: PDF export
        print(f"[Phase 10] Exporting PDF for '{problem.id}'...")
        monitor.emit("phase_start", {"phase": "pdf", "problem_id": problem.id})
        try:
            pdf_path = await asyncio.to_thread(run_pdf_converter, paper_path)
            err = validate_pdf(pdf_path)
            if err:
                monitor.emit("phase_error", {"phase": "pdf", "problem_id": problem.id, "error": err})
                await healer.heal("pdf", err, context=ctx)
            else:
                monitor.emit("phase_end", {"phase": "pdf", "problem_id": problem.id})
        except Exception as e:
            monitor.emit("phase_error", {"phase": "pdf", "problem_id": problem.id, "error": str(e)})
            await healer.heal("pdf", f"Phase crashed: {e}", context=ctx)
            pdf_path = None

        print(f"\n[Done] Problem '{problem.id}' complete.")
        print(f"  Output folder: {problem_dir}/")
        if pdf_path:
            print(f"  PDF:           {pdf_path}")

    # Save metrics and healer summary
    monitor.emit("pipeline_end", {"problems_completed": len(problem_dirs)})
    collector.save(Path("outputs/metrics_report.json"))
    collector.print_summary()
    healer.save_summary()

    print(f"\n{'='*60}")
    print("Pipeline complete!")
    print(f"Outputs:")
    print(f"  problems.json          -> outputs/problems.json")
    print(f"  sub_agent_reports/     -> outputs/sub_agent_reports/")
    print(f"  test_results.json      -> outputs/test_results.json")
    print(f"  metrics_report.json    -> outputs/metrics_report.json")
    print(f"  lessons_learned.json   -> outputs/lessons_learned.json")
    for pid in problem_dirs:
        print(f"  {pid}/  -> outputs/{pid}/")
    print(f"{'='*60}\n")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Problem-to-Paper pipeline")
    parser.add_argument(
        "--topic",
        default="LLM efficiency and compression",
        help="Seed topic to discover problems around",
    )
    parser.add_argument(
        "--agent",
        choices=["qwen", "claude"],
        default="qwen",
        help="Which agent CLI to use: 'qwen' (/opt/homebrew/bin/qwen) or 'claude' (default: qwen)",
    )
    parser.add_argument(
        "--max-problems",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of gathered problems to evaluate (default: all)",
    )
    parser.add_argument(
        "--max-accepted",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of accepted problems to process through phases 3-9 (default: all)",
    )
    parser.add_argument(
        "--max-research",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of sub-agent research tasks to run (default: all)",
    )
    args = parser.parse_args()
    asyncio.run(main(
        seed_topic=args.topic,
        max_problems=args.max_problems,
        max_accepted=args.max_accepted,
        max_research=args.max_research,
        agent=args.agent,
    ))


if __name__ == "__main__":
    cli()
