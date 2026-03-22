"""Classify user intent and extract tool arguments via LLM."""

from typing import Any, Dict
import json
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are an intent classifier for an AI assistant with these tools:

1. **chat** - General conversation, greetings, questions, help
2. **research** - Deep research on a topic (starts a multi-phase research pipeline that produces papers). Use when user asks to research, investigate, or study something in depth.
3. **web_fetch** - Fetch content from a specific URL. Use when user provides a URL or asks to read/fetch a webpage.
4. **security** - Network security tools, WiFi auditing, penetration testing, vulnerability scanning, password cracking, MITM analysis, exploitation. Use when user asks to scan, audit, hack, crack, intercept, exploit, pentest, or use security tools.

Classify the user's message and extract any arguments.

RESPOND ONLY with valid JSON in this exact format:
{"intent": "chat|research|web_fetch|security", "tool_args": {}}

For research: {"intent": "research", "tool_args": {"topic": "the research topic"}}
For web_fetch: {"intent": "web_fetch", "tool_args": {"url": "https://..."}}
For security: {"intent": "security", "tool_args": {"target_tools": null, "parameters": null}}
For chat: {"intent": "chat", "tool_args": {}}

User message: {message}

JSON:"""


def classify_intent(state: RouterGraphState) -> Dict[str, Any]:
    """Use LLM to classify the user's intent."""
    from app.config import config
    import httpx

    message = state.get("message", "")

    # Build the prompt
    prompt = CLASSIFICATION_PROMPT.format(message=message)

    try:
        client = httpx.Client(timeout=30.0)
        resp = client.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": config.LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},  # Low temp for classification
            },
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()
        client.close()

        # Parse JSON from response
        parsed = _extract_json(raw)
        intent = parsed.get("intent", "chat")
        tool_args = parsed.get("tool_args", {})

        # Validate intent
        if intent not in ("chat", "research", "web_fetch", "security"):
            intent = "chat"

        logger.info(f"Classified intent: {intent}, args: {tool_args}")

        return {
            "intent": intent,
            "tool_args": tool_args,
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}, defaulting to chat")
        return {
            "intent": "chat",
            "tool_args": {},
        }


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences and extra text."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in the text
    for start_char in ["{", "```json\n{"]:
        idx = text.find("{")
        if idx != -1:
            # Find matching closing brace
            depth = 0
            for i in range(idx, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[idx : i + 1])
                        except json.JSONDecodeError:
                            break
            break

    return {"intent": "chat", "tool_args": {}}
