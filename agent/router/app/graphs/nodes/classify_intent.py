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
5. **visual** - User asks about what they see, what's happening around them, what they're doing, what's on their screen, or asks you to look at/describe something from the camera. Use when the user wants you to observe or describe the visual scene.
6. **code_analysis** - Analyze a source code repository or codebase. Use when the user asks to analyze a repo, find what calls a function, list API routes/endpoints, show architecture, find dependencies, understand code structure, or asks code-understanding questions referencing a GitHub URL or local path. Extract repo_url if a GitHub URL (https://github.com/...) is present in the message.
7. **solana_trade** - Direct, single-shot Solana wallet operations: check SOL/SPL balance, look up a token price or mint info, execute an explicitly-stated swap or transfer when the user gives both the source/destination and an exact amount. Extract op (one of: balance, swap, transfer, price, token_info) and a params object.
8. **solana_strategy** - Solana trading questions that need analysis BEFORE acting: "should I buy X?", "is now a good time to swap?", indicator-based decisions, momentum / RSI / Bollinger queries, or any "what should I do" trade question. Strategy emits an intent for the user to confirm — it never directly executes.

Classify the user's message and extract any arguments.

RESPOND ONLY with valid JSON in this exact format:
{{"intent": "chat|research|web_fetch|security|visual|code_analysis|solana_trade|solana_strategy", "tool_args": {{}}}}

For research: {{"intent": "research", "tool_args": {{"topic": "the research topic"}}}}
For web_fetch: {{"intent": "web_fetch", "tool_args": {{"url": "https://..."}}}}
For security: {{"intent": "security", "tool_args": {{"target_tools": null, "parameters": null}}}}
For visual: {{"intent": "visual", "tool_args": {{}}}}
For chat: {{"intent": "chat", "tool_args": {{}}}}
For code_analysis: {{"intent": "code_analysis", "tool_args": {{"repo_url": "https://github.com/owner/repo", "repo_path": null}}}}
For solana_trade: {{"intent": "solana_trade", "tool_args": {{"op": "balance|swap|transfer|price|token_info", "params": {{}}, "token": "<mint>", "mint": "<mint>"}}}}
For solana_strategy: {{"intent": "solana_strategy", "tool_args": {{"confirmed": false}}}}

User message: {message}

JSON:"""


def classify_intent(state: RouterGraphState) -> Dict[str, Any]:
    """Use LLM to classify the user's intent."""
    # If intent was already set (e.g. by the WS handler's phase-1 pre-classify),
    # skip the LLM call to avoid a redundant round-trip.
    if state.get("intent") in ("chat", "research", "web_fetch", "security", "visual", "code_analysis", "solana_trade", "solana_strategy"):
        logger.info(f"Intent already classified: {state['intent']}, skipping LLM call")
        return {}

    from app.config import config
    import httpx

    message = state.get("message", "")

    # Build the prompt
    prompt = CLASSIFICATION_PROMPT.format(message=message)

    try:
        client = httpx.Client(timeout=30.0)
        if config.LLM_PROVIDER == "openai":
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json={
                    "model": config.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
        else:
            resp = client.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": config.LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
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
        if intent not in ("chat", "research", "web_fetch", "security", "visual", "code_analysis", "solana_trade", "solana_strategy"):
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
