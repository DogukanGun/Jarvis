"""Phase 8.5: Generate figures from pipeline data."""
from __future__ import annotations
from pathlib import Path

from ..models import ExecutionPlan, TestResults, ComparisonReport


def run_visualizer(
    plan: ExecutionPlan,
    test_results: TestResults,
    comparison: ComparisonReport,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    """Generate PNG figures for the paper. Returns only figures that were written."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[visualize] matplotlib not installed — skipping figure generation")
        return {}

    if out_dir is not None:
        figures_dir = out_dir / "figures"
    else:
        figures_dir = Path("outputs/figures") / plan.problem_id
    figures_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Path] = {}

    # --- pipeline_flow.png ---
    if plan.steps:
        fig, ax = plt.subplots(figsize=(6, max(4, len(plan.steps) * 0.8)))
        ax.axis("off")
        n = len(plan.steps)
        for i, step in enumerate(plan.steps):
            y = 1.0 - i / max(n, 1)
            label = step if len(step) <= 60 else step[:57] + "..."
            ax.text(
                0.5, y, f"{i+1}. {label}",
                ha="center", va="center",
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#d0e8ff", edgecolor="#3a7abf"),
                transform=ax.transAxes,
            )
            if i < n - 1:
                ax.annotate(
                    "", xy=(0.5, 1.0 - (i + 1) / max(n, 1) + 0.02),
                    xytext=(0.5, y - 0.03),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color="#3a7abf"),
                )
        ax.set_title("Implementation Pipeline", fontsize=11, fontweight="bold", pad=10)
        path = figures_dir / "pipeline_flow.png"
        fig.tight_layout()
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        result["pipeline_flow"] = path
        print(f"[visualize] Saved {path}")

    # --- metrics_chart.png ---
    if test_results.metrics:
        labels = list(test_results.metrics.keys())
        values = list(test_results.metrics.values())
        fig, ax = plt.subplots(figsize=(6, max(3, len(labels) * 0.5)))
        colors = ["#4caf50" if v >= 0 else "#f44336" for v in values]
        bars = ax.barh(labels, values, color=colors, edgecolor="white")
        ax.bar_label(bars, fmt="%.3g", padding=3, fontsize=8)
        ax.set_xlabel("Value")
        ax.set_title("Evaluation Metrics", fontsize=11, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        path = figures_dir / "metrics_chart.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        result["metrics_chart"] = path
        print(f"[visualize] Saved {path}")

    # --- comparison_chart.png ---
    systems = comparison.compared_systems
    if systems:
        strengths = comparison.strengths
        weaknesses = comparison.weaknesses
        # Build a simple grouped bar: count of strengths/weaknesses per system
        n = min(len(systems), 8)  # cap to avoid crowded chart
        systems = systems[:n]
        str_counts = [
            sum(1 for s in strengths if any(sys.lower() in s.lower() for sys in [systems[i]]))
            for i in range(n)
        ]
        wk_counts = [
            sum(1 for w in weaknesses if any(sys.lower() in w.lower() for sys in [systems[i]]))
            for i in range(n)
        ]
        # Fallback: if all zeros, show uniform 1s to still render something useful
        if all(v == 0 for v in str_counts + wk_counts):
            str_counts = [len(strengths)] + [0] * (n - 1)
            wk_counts = [len(weaknesses)] + [0] * (n - 1)

        x = range(n)
        width = 0.35
        fig, ax = plt.subplots(figsize=(max(5, n * 1.2), 4))
        ax.bar([i - width / 2 for i in x], str_counts, width, label="Strengths", color="#4caf50")
        ax.bar([i + width / 2 for i in x], wk_counts, width, label="Weaknesses", color="#f44336")
        ax.set_xticks(list(x))
        short_labels = [s[:20] for s in systems]
        ax.set_xticklabels(short_labels, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("Count")
        ax.set_title("Comparison with Baselines", fontsize=11, fontweight="bold")
        ax.legend()
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        path = figures_dir / "comparison_chart.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        result["comparison_chart"] = path
        print(f"[visualize] Saved {path}")

    return result
