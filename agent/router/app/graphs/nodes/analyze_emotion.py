"""Analyze the emotional tone of a user message via keyword rules.

Replaced the previous GPT-4o LLM call (which added ~15-30s per message)
with a fast keyword/pattern approach. Accuracy is sufficient for the
purpose of subtle tone adaptation in generate_response.
"""

import re
from typing import Any, Dict

from ..state import RouterGraphState

_DEFAULT_EMOTION = {
    "emotion": "neutral",
    "valence": 0.0,
    "arousal": 0.3,
    "confidence": 0.5,
}

# (pattern, emotion, valence, arousal, confidence)
_RULES: list[tuple[re.Pattern, str, float, float, float]] = [
    (re.compile(r"\b(thank|thanks|appreciate|grateful|awesome|great|love it|perfect)\b", re.I),
     "grateful",  0.7, 0.3, 0.8),
    (re.compile(r"\b(hi|hello|hey|howdy|sup|yo)\b", re.I),
     "happy",     0.3, 0.2, 0.7),
    (re.compile(r"\b(happy|excited|amazing|fantastic|wonderful|yay|😊|🎉)\b", re.I),
     "excited",   0.8, 0.7, 0.8),
    (re.compile(r"\b(sad|unhappy|depressed|down|crying|😢|😭)\b", re.I),
     "sad",      -0.6, 0.5, 0.8),
    (re.compile(r"\b(angry|annoyed|furious|frustrated|ugh|wtf|damn|hate)\b", re.I),
     "frustrated",-0.5, 0.7, 0.8),
    (re.compile(r"\b(anxious|worried|nervous|scared|afraid|stress)\b", re.I),
     "anxious",  -0.4, 0.6, 0.8),
    (re.compile(r"\b(confused|don'?t understand|unclear|lost|huh|what\?)\b", re.I),
     "confused", -0.1, 0.4, 0.7),
    (re.compile(r"\b(why|how|what|who|when|where|research|explain|curious|interesting)\b", re.I),
     "curious",   0.2, 0.5, 0.6),
]


def analyze_emotion(state: RouterGraphState) -> Dict[str, Any]:
    """Rule-based emotion classification — runs in microseconds."""
    message = state.get("message", "")
    if not message:
        return {"emotion_analysis": _DEFAULT_EMOTION}

    for pattern, emotion, valence, arousal, confidence in _RULES:
        if pattern.search(message):
            return {"emotion_analysis": {
                "emotion": emotion,
                "valence": valence,
                "arousal": arousal,
                "confidence": confidence,
            }}

    return {"emotion_analysis": _DEFAULT_EMOTION}
