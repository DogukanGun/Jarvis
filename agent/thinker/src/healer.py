"""Self-healing system: detects phase failures, fixes source code, logs lessons."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from .metrics import MetricsCollector


HEALER_PROMPT = """You are a self-healing pipeline engineer. A phase in an automated research pipeline has failed.

Your job:
1. Read the error and the relevant source files
2. Read the past lessons to understand what has already been tried
3. Edit the source code to fix the ROOT CAUSE so this failure never happens again
4. Return a JSON summary of what you fixed

RULES:
- Fix the source code files (src/pipeline/*.py, src/prompts/*.py) — NOT the output files
- Make minimal, targeted changes — don't refactor or restructure
- If the issue is in a prompt, fix the prompt. If it's in parsing logic, fix the parser.
- If a past lesson already addressed this exact issue and it's still failing, try a DIFFERENT approach
- Do NOT break existing functionality — only add guards/fixes

After making your edits, return ONLY this JSON:
{{"fix_description": "what you changed and why", "files_modified": ["list", "of", "files"]}}
"""


# ---------------------------------------------------------------------------
# Validators — return None on success, error string on failure
# ---------------------------------------------------------------------------

def validate_gather(problems: list) -> str | None:
    if not problems:
        return "Gatherer returned 0 problems"
    return None


def validate_evaluate(decision: str, problem_id: str) -> str | None:
    if decision not in ("accept", "reject"):
        return f"Evaluator returned '{decision}' for {problem_id} — expected 'accept' or 'reject'"
    return None


def validate_decompose(sub_problems: list, problem_id: str) -> str | None:
    if not sub_problems:
        return f"Decomposer returned 0 sub-problems for {problem_id}"
    return None


def validate_research(reports: list) -> str | None:
    if not reports:
        return "Research swarm returned 0 reports"
    empty = [r for r in reports if not getattr(r, "findings", "")]
    if empty:
        return f"{len(empty)} research reports have empty findings"
    return None


def validate_plan(plan, problem_id: str) -> str | None:
    if not plan.steps:
        return f"Planner returned empty steps for {problem_id}"
    if "Unable to parse" in plan.chosen_direction:
        return f"Planner failed to parse plan for {problem_id}: {plan.chosen_direction}"
    return None


def validate_code(code_dir: Path, problem_id: str) -> str | None:
    if not code_dir.exists():
        return f"Code directory does not exist: {code_dir}"
    py_files = list(code_dir.glob("*.py"))
    if not py_files:
        return f"Code directory has no .py files: {code_dir}"
    return None


def validate_test(test_results, problem_id: str) -> str | None:
    if not test_results.passed and test_results.output.startswith("No output"):
        return f"Tester returned no output for {problem_id} — agent likely failed"
    if not test_results.metrics and not test_results.passed:
        return f"Tester returned passed=False with empty metrics for {problem_id} — possible parse failure"
    return None


def validate_compare(comparison, problem_id: str) -> str | None:
    if not comparison.compared_systems:
        return f"Comparator returned no compared systems for {problem_id}"
    return None


def validate_write(paper_path: Path) -> str | None:
    if not paper_path.exists():
        return f"Paper file does not exist: {paper_path}"
    content = paper_path.read_text()
    if not content.strip().startswith("\\documentclass"):
        first_line = content.split("\n")[0][:100]
        return f"Paper .tex does not start with \\documentclass — starts with: '{first_line}'"
    if "\\end{document}" not in content:
        return "Paper .tex is missing \\end{{document}}"
    return None


def validate_pdf(pdf_path: Path | None) -> str | None:
    if pdf_path is None or not pdf_path.exists():
        return "PDF was not produced — pdflatex failed"
    return None


# ---------------------------------------------------------------------------
# Phase → source files mapping
# ---------------------------------------------------------------------------

PHASE_SOURCE_FILES = {
    "gather": ["src/pipeline/gather.py", "src/prompts/gatherer.py"],
    "evaluate": ["src/pipeline/evaluate.py", "src/prompts/evaluator.py"],
    "decompose": ["src/pipeline/decompose.py", "src/prompts/decomposer.py"],
    "research": ["src/pipeline/research.py", "src/prompts/sub_agent.py"],
    "plan": ["src/pipeline/plan.py", "src/prompts/planner.py"],
    "code": ["src/pipeline/code.py", "src/prompts/coder.py"],
    "test": ["src/pipeline/test.py", "src/prompts/tester.py"],
    "compare": ["src/pipeline/compare.py", "src/prompts/comparator.py"],
    "write": ["src/pipeline/write.py", "src/prompts/writer.py"],
    "pdf": ["src/pipeline/pdf.py", "src/pipeline/write.py"],
}


# ---------------------------------------------------------------------------
# Healer class
# ---------------------------------------------------------------------------

class Healer:
    """Spawns a Claude agent to fix pipeline source code when a phase fails."""

    def __init__(self, cli_path: str, lessons_path: Path, metrics: MetricsCollector | None = None):
        self.cli_path = cli_path
        self.lessons_path = lessons_path
        self.metrics = metrics
        self.lessons: list[dict] = self._load_lessons()
        self.invocations: int = 0

    def _load_lessons(self) -> list[dict]:
        if self.lessons_path.exists():
            try:
                return json.loads(self.lessons_path.read_text())
            except Exception:
                return []
        return []

    def get_lessons_for_phase(self, phase: str) -> str:
        relevant = [l for l in self.lessons if l.get("phase") == phase]
        if not relevant:
            return "No past lessons for this phase."
        lines = []
        for l in relevant[-5:]:  # Last 5 lessons for this phase
            lines.append(f"- [{l.get('timestamp', '?')}] Error: {l.get('error', '?')}")
            lines.append(f"  Fix: {l.get('fix', '?')}")
            lines.append(f"  Files: {', '.join(l.get('files_modified', []))}")
        return "\n".join(lines)

    async def heal(self, phase: str, error: str, context: str = "") -> None:
        """Spawn a healer agent to fix the source code for a failed phase."""
        self.invocations += 1
        source_files = PHASE_SOURCE_FILES.get(phase, [])
        past_lessons = self.get_lessons_for_phase(phase)

        file_list = "\n".join(f"- {f}" for f in source_files)

        prompt = (
            f"{HEALER_PROMPT}\n\n"
            f"## Failed Phase: {phase}\n\n"
            f"## Error:\n{error}\n\n"
            f"## Context:\n{context}\n\n"
            f"## Source files to read and potentially fix:\n{file_list}\n\n"
            f"## Past lessons for this phase:\n{past_lessons}\n\n"
            f"Read the source files listed above, understand the root cause, "
            f"edit the code to fix it, then return the JSON summary."
        )

        print(f"[healer] Phase '{phase}' failed: {error[:100]}...")
        print(f"[healer] Spawning healer agent to fix source code...")

        result = ""
        last_msg = None
        try:
            async for msg in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    allowed_tools=["Read", "Edit", "Write"],
                    cli_path=self.cli_path,
                ),
            ):
                last_msg = msg
                if hasattr(msg, "result") and msg.result:
                    result = msg.result

            if self.metrics:
                self.metrics.record("healer", last_msg, problem_id=f"heal-{phase}")

            # Parse the healer's fix summary
            fix_desc, files_mod = self._parse_fix_summary(result)
            self._log_lesson(phase, error, fix_desc, files_mod)
            print(f"[healer] Fix applied: {fix_desc}")

        except Exception as e:
            print(f"[healer] Healer itself failed: {e} — continuing pipeline")
            self._log_lesson(phase, error, f"Healer failed: {e}", [])

    def _parse_fix_summary(self, text: str) -> tuple[str, list[str]]:
        """Extract fix_description and files_modified from healer output."""
        # Try to find JSON in the response
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            brace = text.find("{", idx)
            if brace == -1:
                break
            try:
                obj, end = decoder.raw_decode(text, brace)
                if isinstance(obj, dict) and "fix_description" in obj:
                    return (
                        obj.get("fix_description", "Unknown fix"),
                        obj.get("files_modified", []),
                    )
                idx = end
            except json.JSONDecodeError:
                idx = brace + 1

        # Fallback: use the whole text as description
        return (text[:500] if text else "No fix description returned", [])

    def _log_lesson(self, phase: str, error: str, fix: str, files_modified: list[str]) -> None:
        lesson = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "phase": phase,
            "error": error[:500],
            "fix": fix[:500],
            "files_modified": files_modified,
        }
        self.lessons.append(lesson)
        self.lessons_path.parent.mkdir(parents=True, exist_ok=True)
        self.lessons_path.write_text(json.dumps(self.lessons, indent=2))

    def save_summary(self) -> None:
        print(f"[healer] Total invocations this run: {self.invocations}")
        if self.invocations > 0:
            print(f"[healer] Lessons logged: {len(self.lessons)} total ({self.invocations} new)")
