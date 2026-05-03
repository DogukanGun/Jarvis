"""Query task-type classifier for legal questions."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)

TASK_TYPES = (
    "JUDGE_STYLE",
    "ELEMENTS_CHECKLIST",
    "STATUTE_EXEGESIS",
    "RISK_ALERT",
    "COMPARATIVE_RULES",
    "PROCEDURE_EVIDENCE_LIST",
)

TOP_K_BY_TASK = {
    "JUDGE_STYLE": 8,
    "ELEMENTS_CHECKLIST": 10,
    "STATUTE_EXEGESIS": 10,
    "RISK_ALERT": 10,
    "COMPARATIVE_RULES": 12,
    "PROCEDURE_EVIDENCE_LIST": 10,
}

MULTIHOP_TASKS = {"COMPARATIVE_RULES", "STATUTE_EXEGESIS"}

_CLASSIFICATION_PROMPT = """Classify this legal question into ONE of these task types:

JUDGE_STYLE - Binary judgment: is X permitted/valid/illegal? What does the court rule?
ELEMENTS_CHECKLIST - What are the required elements/conditions/prerequisites for X?
STATUTE_EXEGESIS - What does Article N mean? Interpret/explain a statute or provision.
RISK_ALERT - What are the risks/penalties/consequences/liabilities for X?
COMPARATIVE_RULES - Compare X across jurisdictions/articles/regimes.
PROCEDURE_EVIDENCE_LIST - What are the procedural steps or evidence requirements for X?

Return JSON only: {{"task_type": "<TYPE>"}}

Question: {question}

JSON:"""


@dataclass
class QueryClassification:
    task_type: str
    top_k: int
    requires_multihop: bool


class QueryRouter:
    async def classify(self, message: str) -> QueryClassification:
        task_type = await self._classify_llm(message)
        if task_type not in TASK_TYPES:
            task_type = self._classify_heuristic(message)
        return QueryClassification(
            task_type=task_type,
            top_k=TOP_K_BY_TASK.get(task_type, 10),
            requires_multihop=task_type in MULTIHOP_TASKS,
        )

    async def _classify_llm(self, message: str) -> str:
        import httpx

        prompt = _CLASSIFICATION_PROMPT.format(question=message)
        try:
            if config.LLM_PROVIDER == "anthropic":
                import anthropic  # type: ignore
                client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                resp = client.messages.create(
                    model=config.ANTHROPIC_MODEL,
                    max_tokens=64,
                    temperature=0.0,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = resp.content[0].text.strip()
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                        json={
                            "model": config.OPENAI_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.0,
                            "max_tokens": 64,
                        },
                    )
                    resp.raise_for_status()
                    raw = resp.json()["choices"][0]["message"]["content"].strip()

            parsed = _extract_json(raw)
            return parsed.get("task_type", "STATUTE_EXEGESIS")
        except Exception as e:
            logger.warning("LLM classification failed: %s", e)
            return "STATUTE_EXEGESIS"

    def _classify_heuristic(self, message: str) -> str:
        m = message.lower()
        if any(w in m for w in ("penalt", "fine", "sanction", "liable", "risk", "violat")):
            return "RISK_ALERT"
        if any(w in m for w in ("compare", "difference", "versus", "vs ", "contrast", "across")):
            return "COMPARATIVE_RULES"
        if any(w in m for w in ("steps", "procedure", "how to", "evidence", "process", "filing")):
            return "PROCEDURE_EVIDENCE_LIST"
        if any(w in m for w in ("element", "requires", "condition", "criteria", "must", "prerequisit")):
            return "ELEMENTS_CHECKLIST"
        if any(w in m for w in ("is it legal", "permitted", "allowed", "valid", "lawful", "illegal")):
            return "JUDGE_STYLE"
        return "STATUTE_EXEGESIS"


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    idx = text.find("{")
    if idx != -1:
        depth = 0
        for i in range(idx, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[idx: i + 1])
                    except json.JSONDecodeError:
                        break
    return {}
