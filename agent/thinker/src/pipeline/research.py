from __future__ import annotations
import json
import re
import signal
import sys
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import SubProblem, SubProblemReport
from ..metrics import MetricsCollector
from ..prompts.sub_agent import SUB_AGENT_PROMPT

# Ignore SIGPIPE at module level so broken pipes raise BrokenPipeError
# instead of killing the process with an unhandled signal.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except (AttributeError, OSError, ValueError):
    pass  # SIGPIPE not available on Windows / not main thread


def _safe_print(msg: str, **kwargs) -> None:
    """Print that silently swallows BrokenPipeError / OSError."""
    try:
        print(msg, **kwargs)
    except (BrokenPipeError, OSError):
        pass


def _extract_json(text: str) -> str:
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _try_parse_report(text: str) -> SubProblemReport | None:
    """Try to parse a single report from text, returning None on failure."""
    if not text:
        return None
    raw = _extract_json(text)
    if not raw:
        return None
    # Try direct parse first
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return SubProblemReport(**data)
    except (json.JSONDecodeError, Exception):
        pass
    # Try to find JSON object in text
    match = re.search(r'\{[^{}]*"sub_problem_id"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return SubProblemReport(**data)
        except Exception:
            pass
    return None


def _collect_result_from_messages(messages: list) -> str:
    """Collect the best result string from a list of SDK messages."""
    # Prefer ResultMessage.result
    for msg in reversed(messages):
        if hasattr(msg, "result") and msg.result:
            return msg.result
    # Fall back to last AssistantMessage content
    for msg in reversed(messages):
        if type(msg).__name__ == "AssistantMessage" and hasattr(msg, "content"):
            parts = []
            for block in (msg.content or []):
                if hasattr(block, "text"):
                    parts.append(block.text)
            if parts:
                return "\n".join(parts)
    return ""


async def _run_single_sub_agent(sp: SubProblem, cli_path: str | None = None, metrics: MetricsCollector | None = None, max_retries: int = 2) -> SubProblemReport | None:
    """Run one sub-agent and return its parsed report.

    Retries on BrokenPipeError / ConnectionError up to max_retries times.
    """
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            prompt = SUB_AGENT_PROMPT.format(
                sub_problem_id=sp.id,
                title=sp.title,
                description=sp.description,
                research_angle=sp.research_angle,
            )
            messages = []
            async for msg in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=["WebSearch", "WebFetch"],
                    cli_path=cli_path,
                ),
            ):
                messages.append(msg)
            if metrics and messages:
                metrics.record("research", messages[-1], problem_id=sp.id)

            result = _collect_result_from_messages(messages)
            report = _try_parse_report(result)

            if report is None:
                # Build a minimal report from whatever text we got
                report = SubProblemReport(
                    sub_problem_id=sp.id,
                    findings=result[:2000] if result else f"Research for: {sp.description}",
                    implementation_plan="1. Investigate further\n2. Review literature\n3. Prototype",
                )
            return report

        except (BrokenPipeError, ConnectionError, OSError) as exc:
            last_err = exc
            _safe_print(f"[research]   ⚠ sub-agent {sp.id} attempt {attempt}/{max_retries} failed: {exc}", file=sys.stderr, flush=True)
            if attempt < max_retries:
                continue
            # Exhausted retries — return a fallback report instead of crashing
            _safe_print(f"[research]   ✗ sub-agent {sp.id} failed after {max_retries} attempts, using fallback", file=sys.stderr, flush=True)
            return SubProblemReport(
                sub_problem_id=sp.id,
                findings=f"Research for: {sp.description} (sub-agent failed: {last_err})",
                implementation_plan="1. Investigate further\n2. Review literature\n3. Prototype",
            )


async def run_research_swarm(sub_problems: list[SubProblem], cli_path: str | None = None, metrics: MetricsCollector | None = None) -> list[SubProblemReport]:
    """Run each sub-agent sequentially and collect reports."""
    out_dir = Path("outputs/sub_agent_reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    reports: list[SubProblemReport] = []
    for i, sp in enumerate(sub_problems, 1):
        _safe_print(f"[research] Running sub-agent {i}/{len(sub_problems)}: {sp.id}", flush=True)
        try:
            report = await _run_single_sub_agent(sp, cli_path=cli_path, metrics=metrics)
        except Exception as exc:
            _safe_print(f"[research]   ✗ sub-agent {sp.id} crashed unexpectedly: {exc}", file=sys.stderr, flush=True)
            report = SubProblemReport(
                sub_problem_id=sp.id,
                findings=f"Research for: {sp.description} (agent error: {exc})",
                implementation_plan="1. Investigate further\n2. Review literature\n3. Prototype",
            )
        if report:
            reports.append(report)
            out_path = out_dir / f"{report.sub_problem_id}.json"
            out_path.write_text(json.dumps(report.model_dump(), indent=2))
            _safe_print(f"[research]   -> saved {out_path.name}", flush=True)

    _safe_print(f"[research] Completed {len(reports)} sub-agent reports")
    return reports
