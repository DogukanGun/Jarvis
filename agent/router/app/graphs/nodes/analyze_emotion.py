"""Analyze the emotional tone of a user message via LLM."""

from typing import Any, Dict
import json
import logging

from ..state import RouterGraphState

logger = logging.getLogger(__name__)

EMOTION_PROMPT = """You are an emotion analysis system. Analyze the emotional tone of the user's message.

Respond ONLY with valid JSON in this exact format:
{{"emotion": "<label>", "valence": <float>, "arousal": <float>, "confidence": <float>}}

Where:
- emotion: one of: neutral, happy, sad, angry, anxious, excited, frustrated, curious, grateful, confused
- valence: emotional positivity from -1.0 (very negative) to 1.0 (very positive)
- arousal: emotional intensity from 0.0 (calm) to 1.0 (very intense)
- confidence: your confidence in this classification from 0.0 to 1.0

User message: {message}

JSON:"""

_DEFAULT_EMOTION = {
    "emotion": "neutral",
    "valence": 0.0,
    "arousal": 0.3,
    "confidence": 0.0,
}


def analyze_emotion(state: RouterGraphState) -> Dict[str, Any]:
    """Use LLM to analyze the emotional tone of the user's message."""
    from app.config import config
    import httpx

    message = state.get("message", "")
    if not message:
        return {"emotion_analysis": _DEFAULT_EMOTION}

    prompt = EMOTION_PROMPT.format(message=message)

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

        parsed = _extract_json(raw)

        # Validate and clamp values
        emotion = parsed.get("emotion", "neutral")
        valid_emotions = {
            "neutral", "happy", "sad", "angry", "anxious",
            "excited", "frustrated", "curious", "grateful", "confused",
        }
        if emotion not in valid_emotions:
            emotion = "neutral"

        valence = max(-1.0, min(1.0, float(parsed.get("valence", 0.0))))
        arousal = max(0.0, min(1.0, float(parsed.get("arousal", 0.3))))
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.0))))

        result = {
            "emotion": emotion,
            "valence": valence,
            "arousal": arousal,
            "confidence": confidence,
        }

        logger.info(f"Emotion analysis: {result}")
        return {"emotion_analysis": result}

    except Exception as e:
        logger.error(f"Emotion analysis failed: {e}, defaulting to neutral")
        return {"emotion_analysis": _DEFAULT_EMOTION}


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences and extra text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for start_char in ["{", "```json\n{"]:
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
                            return json.loads(text[idx : i + 1])
                        except json.JSONDecodeError:
                            break
            break

    return _DEFAULT_EMOTION
