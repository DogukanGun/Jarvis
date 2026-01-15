"""
Preprocess Node for Jarvis MainGraph
Node 1: preprocess_input

Deterministic preprocessing of user prompts into structured fields.
No LLM calls - fast and rule-based only.
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional

from app.shared.types import MainGraphState


class TaskType(Enum):
    """Task types detected from user prompts"""
    CHAT = "chat"
    SEND_EMAIL = "send_email"
    FILL_FORM = "fill_form"
    SEARCH_BROWSE = "search_browse"
    LOGIN_AUTH = "login_auth"
    FILES_DOWNLOAD_UPLOAD = "files_download_upload"
    UNKNOWN = "unknown"


# Priority order for task type detection (higher index = higher priority)
TASK_TYPE_PRIORITY = [
    TaskType.UNKNOWN,
    TaskType.CHAT,
    TaskType.SEARCH_BROWSE,
    TaskType.FILL_FORM,
    TaskType.FILES_DOWNLOAD_UPLOAD,
    TaskType.SEND_EMAIL,
    TaskType.LOGIN_AUTH,
]


# Keyword mappings for task type detection
TASK_TYPE_KEYWORDS = {
    TaskType.SEND_EMAIL: [
        "send email", "email to", "mail to", "write an email",
        "compose email", "draft email", "forward email", "reply to"
    ],
    TaskType.FILL_FORM: [
        "fill form", "application", "apply", "submit", "registration",
        "sign up form", "complete form", "form submission", "fill out"
    ],
    TaskType.SEARCH_BROWSE: [
        "search", "find", "look up", "browse", "google", "research",
        "search for", "look for", "find information"
    ],
    TaskType.LOGIN_AUTH: [
        "login", "log in", "sign in", "2fa", "otp", "authenticate",
        "two factor", "verification code", "authentication"
    ],
    TaskType.FILES_DOWNLOAD_UPLOAD: [
        "upload", "download", "attach file", "pdf", "document",
        "attachment", "file upload", "file download", "save file"
    ],
}


# Known app keywords
APP_KEYWORDS = {
    "gmail": ["gmail", "google mail"],
    "outlook": ["outlook", "microsoft mail"],
    "linkedin": ["linkedin"],
    "kvr": ["kvr"],
    "google": ["google"],
    "microsoft": ["microsoft"],
    "slack": ["slack"],
    "discord": ["discord"],
}


def normalize_text(text: str) -> str:
    """
    Normalize input text by stripping and collapsing whitespace.

    Args:
        text: Raw input text

    Returns:
        Normalized text with stripped whitespace and collapsed spaces
    """
    if not text:
        return ""

    # Strip leading/trailing whitespace
    text = text.strip()

    # Collapse multiple whitespace characters into single spaces
    text = re.sub(r'\s+', ' ', text)

    return text


def detect_task_type(normalized_prompt: str) -> tuple[TaskType, List[str]]:
    """
    Detect task type from normalized prompt using keyword matching.

    Priority order (highest to lowest):
    LOGIN_AUTH > SEND_EMAIL > FILES_DOWNLOAD_UPLOAD > FILL_FORM >
    SEARCH_BROWSE > CHAT > UNKNOWN

    Args:
        normalized_prompt: Normalized prompt text

    Returns:
        Tuple of (detected_task_type, matched_keywords)
    """
    prompt_lower = normalized_prompt.lower()

    matched_types = {}

    # Check each task type for keyword matches
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in prompt_lower]
        if matched:
            matched_types[task_type] = matched

    # If no matches, determine CHAT vs UNKNOWN
    if not matched_types:
        # CHAT: short conversational prompts (< 50 chars, no special patterns)
        if len(normalized_prompt) < 50 and not re.search(r'https?://', normalized_prompt):
            return TaskType.CHAT, []
        else:
            return TaskType.UNKNOWN, []

    # If multiple matches, pick highest priority
    if len(matched_types) > 1:
        highest_priority_type = max(
            matched_types.keys(),
            key=lambda t: TASK_TYPE_PRIORITY.index(t)
        )
        return highest_priority_type, matched_types[highest_priority_type]

    # Single match
    task_type = list(matched_types.keys())[0]
    return task_type, matched_types[task_type]


def detect_app(normalized_prompt: str, task_type: TaskType, context: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Detect application from prompt or context.

    Args:
        normalized_prompt: Normalized prompt text
        task_type: Detected task type
        context: Optional context dictionary

    Returns:
        Detected app name or None
    """
    prompt_lower = normalized_prompt.lower()

    # First, check for explicit app mentions in prompt
    for app_name, keywords in APP_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                return app_name

    # If not found in prompt, check context
    if context and "current_app" in context:
        current_app = context["current_app"]

        # Only use context app if it's compatible with task type
        compatible_apps = {
            TaskType.SEND_EMAIL: ["gmail", "outlook"],
            TaskType.FILL_FORM: ["linkedin", "google", "kvr"],
            TaskType.LOGIN_AUTH: ["gmail", "outlook", "linkedin", "kvr"],
        }

        if task_type in compatible_apps:
            if current_app in compatible_apps[task_type]:
                return current_app

    return None


def extract_entities(normalized_prompt: str, detected_app: Optional[str]) -> tuple[List[str], Dict[str, Any]]:
    """
    Extract entities from normalized prompt.

    Entities include:
    - URLs
    - Email addresses
    - Capitalized token sequences (potential names)
    - Detected app name

    Args:
        normalized_prompt: Normalized prompt text
        detected_app: Detected app name

    Returns:
        Tuple of (entities_list, extraction_meta)
    """
    entities = []
    extraction_meta = {
        "urls": 0,
        "emails": 0,
        "names": 0,
        "methods": []
    }

    # Extract URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, normalized_prompt)
    if urls:
        entities.extend(urls)
        extraction_meta["urls"] = len(urls)
        extraction_meta["methods"].append("url_regex")

    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, normalized_prompt)
    if emails:
        entities.extend(emails)
        extraction_meta["emails"] = len(emails)
        extraction_meta["methods"].append("email_regex")

    # Extract capitalized sequences (potential names)
    # Match sequences of 2+ capitalized words
    name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    names = re.findall(name_pattern, normalized_prompt)
    if names:
        entities.extend(names)
        extraction_meta["names"] = len(names)
        extraction_meta["methods"].append("capitalized_sequences")

    # Add detected app if present
    if detected_app:
        entities.append(detected_app)
        extraction_meta["methods"].append("app_detection")

    # Deduplicate while preserving order
    seen = set()
    deduplicated = []
    for entity in entities:
        if entity not in seen:
            seen.add(entity)
            deduplicated.append(entity)

    return deduplicated, extraction_meta


def preprocess_input(state: MainGraphState) -> Dict[str, Any]:
    """
    Main preprocessing node for MainGraph.

    Converts raw prompt into structured fields:
    - normalized_prompt
    - task_type
    - app
    - entities
    - preprocess_meta

    Args:
        state: Graph state containing 'prompt' and optional 'context'

    Returns:
        Dictionary of state updates
    """
    prompt = state.get("prompt", "")
    context = state.get("context")

    # Store original prompt for debugging
    original_prompt = prompt

    # Step 1: Normalize
    normalized_prompt = normalize_text(prompt)

    # Step 2: Detect task type
    task_type, matched_keywords = detect_task_type(normalized_prompt)

    # Step 3: Detect app
    app = detect_app(normalized_prompt, task_type, context)

    # Step 4: Extract entities
    entities, extraction_meta = extract_entities(normalized_prompt, app)

    # Build metadata for debugging
    preprocess_meta = {
        "original_prompt": original_prompt,
        "original_length": len(original_prompt),
        "normalized_length": len(normalized_prompt),
        "matched_keywords": matched_keywords,
        "extraction_meta": extraction_meta,
    }

    # Return state updates
    return {
        "normalized_prompt": normalized_prompt,
        "task_type": task_type.value,
        "app": app,
        "entities": entities,
        "preprocess_meta": preprocess_meta,
    }
