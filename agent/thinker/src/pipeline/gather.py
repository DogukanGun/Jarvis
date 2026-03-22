from __future__ import annotations
import json
import re
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from ..models import Problem
from ..metrics import MetricsCollector
from ..prompts.gatherer import GATHERER_PROMPT


def _extract_json(text: str) -> str:
    """Strip markdown fences if present and return raw JSON string."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_problems(text: str) -> list[Problem]:
    raw = _extract_json(text)
    data = json.loads(raw)
    return [Problem(**item) for item in data]


async def run_gatherer(seed_topic: str, cli_path: str | None = None, metrics: MetricsCollector | None = None) -> list[Problem]:
    result = ""
    last_msg = None
    async for msg in query(
        prompt=f"{GATHERER_PROMPT}\n\nSeed topic: {seed_topic}",
        options=ClaudeAgentOptions(
            allowed_tools=["WebSearch", "WebFetch"],
            cli_path=cli_path,
        ),
    ):
        last_msg = msg
        if hasattr(msg, "result") and msg.result:
            result = msg.result
    if metrics:
        metrics.record("gather", last_msg)

    problems = _parse_problems(result)

    out_path = Path("outputs/problems.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([p.model_dump() for p in problems], indent=2))
    print(f"[gatherer] Saved {len(problems)} problems to {out_path}")
    return problems
