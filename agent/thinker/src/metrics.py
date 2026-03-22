"""Pipeline metrics collection and reporting."""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class StepMetrics:
    phase: str
    problem_id: str | None
    cost_usd: float
    tokens: int
    duration_ms: int
    api_duration_ms: int
    tool_uses: int
    turns: int


class MetricsCollector:
    """Accumulates per-step metrics from Claude Agent SDK ResultMessages."""

    def __init__(self, topic: str):
        self.run_id = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.topic = topic
        self.steps: list[StepMetrics] = []

    def record(self, phase: str, result_msg, problem_id: str | None = None) -> None:
        """Extract metrics from a ResultMessage and store them."""
        if result_msg is None:
            return

        usage = getattr(result_msg, "usage", None) or {}
        step = StepMetrics(
            phase=phase,
            problem_id=problem_id,
            cost_usd=getattr(result_msg, "total_cost_usd", None) or 0.0,
            tokens=usage.get("total_tokens", 0) if isinstance(usage, dict) else getattr(usage, "total_tokens", 0),
            duration_ms=getattr(result_msg, "duration_ms", 0) or 0,
            api_duration_ms=getattr(result_msg, "duration_api_ms", 0) or 0,
            tool_uses=usage.get("tool_uses", 0) if isinstance(usage, dict) else getattr(usage, "tool_uses", 0),
            turns=getattr(result_msg, "num_turns", 0) or 0,
        )
        self.steps.append(step)

    def _aggregate(self, steps: list[StepMetrics]) -> dict:
        return {
            "cost_usd": round(sum(s.cost_usd for s in steps), 6),
            "tokens": sum(s.tokens for s in steps),
            "duration_ms": sum(s.duration_ms for s in steps),
            "api_duration_ms": sum(s.api_duration_ms for s in steps),
            "tool_uses": sum(s.tool_uses for s in steps),
            "turns": sum(s.turns for s in steps),
        }

    def build_report(self) -> dict:
        # Per-problem aggregation
        per_problem: dict[str, dict] = {}
        for s in self.steps:
            if s.problem_id:
                if s.problem_id not in per_problem:
                    per_problem[s.problem_id] = []
                per_problem[s.problem_id].append(s)

        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "total": self._aggregate(self.steps),
            "phases": [asdict(s) for s in self.steps],
            "per_problem": {
                pid: self._aggregate(steps)
                for pid, steps in per_problem.items()
            },
        }

    def save(self, out_path: Path) -> None:
        """Write the full metrics report as JSON."""
        report = self.build_report()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2))
        print(f"[metrics] Report saved to {out_path}")

    def print_summary(self) -> None:
        """Print a human-readable summary table."""
        report = self.build_report()
        total = report["total"]

        print(f"\n{'='*60}")
        print("METRICS SUMMARY")
        print(f"{'='*60}")
        print(f"  Total cost:       ${total['cost_usd']:.4f}")
        print(f"  Total tokens:     {total['tokens']:,}")
        print(f"  Total duration:   {total['duration_ms'] / 1000:.1f}s")
        print(f"  API duration:     {total['api_duration_ms'] / 1000:.1f}s")
        print(f"  Tool uses:        {total['tool_uses']}")
        print(f"  Turns:            {total['turns']}")

        if report["per_problem"]:
            print(f"\n  Per problem:")
            for pid, agg in report["per_problem"].items():
                print(f"    {pid}: ${agg['cost_usd']:.4f} | {agg['tokens']:,} tokens | {agg['duration_ms'] / 1000:.1f}s")

        print(f"\n  Per phase:")
        for step in report["phases"]:
            pid = step["problem_id"] or "global"
            print(f"    {step['phase']:20s} [{pid}]: ${step['cost_usd']:.4f} | {step['tokens']:,} tokens | {step['duration_ms'] / 1000:.1f}s")
        print(f"{'='*60}")
