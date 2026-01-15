"""
Unit tests for preprocess_node.py

Tests cover:
- Task type detection
- Priority rules
- App detection from prompt and context
- Entity extraction
- Edge cases and defaults
"""

import pytest
from preprocess_node import (
    TaskType,
    normalize_text,
    detect_task_type,
    detect_app,
    extract_entities,
    preprocess_input,
    GraphState,
)


class TestNormalizeText:
    """Tests for normalize_text function"""

    def test_strip_whitespace(self):
        assert normalize_text("  hello world  ") == "hello world"

    def test_collapse_multiple_spaces(self):
        assert normalize_text("hello    world") == "hello world"

    def test_collapse_mixed_whitespace(self):
        assert normalize_text("hello\t\n  world") == "hello world"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_whitespace_only(self):
        assert normalize_text("   \t\n  ") == ""


class TestDetectTaskType:
    """Tests for detect_task_type function"""

    def test_send_email_detection(self):
        prompt = "send email to john@example.com about the meeting"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.SEND_EMAIL
        assert "send email" in keywords or "email to" in keywords

    def test_send_email_variant(self):
        prompt = "compose email to the team"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.SEND_EMAIL
        assert "compose email" in keywords

    def test_login_detection(self):
        prompt = "login to gmail with 2fa"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.LOGIN_AUTH
        assert any(kw in ["login", "log in", "2fa"] for kw in keywords)

    def test_login_detection_priority_over_email(self):
        """LOGIN_AUTH should have priority over SEND_EMAIL"""
        prompt = "login to send email"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.LOGIN_AUTH

    def test_fill_form_detection(self):
        prompt = "fill form for job application"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.FILL_FORM
        assert any(kw in ["fill form", "application", "apply"] for kw in keywords)

    def test_search_browse_detection(self):
        prompt = "search for the latest news"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.SEARCH_BROWSE
        assert "search" in keywords or "search for" in keywords

    def test_files_upload_detection(self):
        prompt = "upload the pdf document"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.FILES_DOWNLOAD_UPLOAD
        assert any(kw in ["upload", "pdf", "document"] for kw in keywords)

    def test_files_download_detection(self):
        prompt = "download the attachment"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.FILES_DOWNLOAD_UPLOAD
        assert "download" in keywords or "attachment" in keywords

    def test_chat_default(self):
        """Short conversational prompts should be CHAT"""
        prompt = "hello"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.CHAT
        assert keywords == []

    def test_chat_short_question(self):
        prompt = "how are you?"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.CHAT

    def test_unknown_long_prompt(self):
        """Long prompts without keywords should be UNKNOWN"""
        prompt = "this is a very long prompt that does not contain any specific task keywords " * 3
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.UNKNOWN

    def test_unknown_with_url(self):
        """Prompts with URLs but no keywords should be UNKNOWN"""
        prompt = "check out https://example.com/page"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.UNKNOWN

    def test_priority_files_over_form(self):
        """FILES_DOWNLOAD_UPLOAD has priority over FILL_FORM"""
        prompt = "upload document to apply for registration"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.FILES_DOWNLOAD_UPLOAD

    def test_priority_email_over_search(self):
        """SEND_EMAIL has priority over SEARCH_BROWSE"""
        prompt = "search contacts and send email"
        task_type, keywords = detect_task_type(prompt)
        assert task_type == TaskType.SEND_EMAIL


class TestDetectApp:
    """Tests for detect_app function"""

    def test_app_detection_from_prompt_gmail(self):
        prompt = "send email via gmail"
        app = detect_app(prompt, TaskType.SEND_EMAIL, None)
        assert app == "gmail"

    def test_app_detection_from_prompt_google_mail(self):
        prompt = "use google mail to send this"
        app = detect_app(prompt, TaskType.SEND_EMAIL, None)
        assert app == "gmail"

    def test_app_detection_from_prompt_outlook(self):
        prompt = "send via outlook"
        app = detect_app(prompt, TaskType.SEND_EMAIL, None)
        assert app == "outlook"

    def test_app_detection_from_prompt_linkedin(self):
        prompt = "fill linkedin application"
        app = detect_app(prompt, TaskType.FILL_FORM, None)
        assert app == "linkedin"

    def test_app_from_context_compatible(self):
        """Context app should be used if compatible with task type"""
        prompt = "send email to john"
        context = {"current_app": "gmail"}
        app = detect_app(prompt, TaskType.SEND_EMAIL, context)
        assert app == "gmail"

    def test_app_from_context_incompatible(self):
        """Context app should NOT be used if incompatible with task type"""
        prompt = "search for information"
        context = {"current_app": "gmail"}
        app = detect_app(prompt, TaskType.SEARCH_BROWSE, context)
        assert app is None

    def test_prompt_overrides_context(self):
        """Explicit mention in prompt should override context"""
        prompt = "send email via outlook"
        context = {"current_app": "gmail"}
        app = detect_app(prompt, TaskType.SEND_EMAIL, context)
        assert app == "outlook"

    def test_no_app_detected(self):
        prompt = "send email to someone"
        app = detect_app(prompt, TaskType.SEND_EMAIL, None)
        assert app is None

    def test_app_from_context_none_context(self):
        prompt = "send email"
        app = detect_app(prompt, TaskType.SEND_EMAIL, None)
        assert app is None


class TestExtractEntities:
    """Tests for extract_entities function"""

    def test_extract_email(self):
        prompt = "send to john.doe@example.com"
        entities, meta = extract_entities(prompt, None)
        assert "john.doe@example.com" in entities
        assert meta["emails"] == 1

    def test_extract_url(self):
        prompt = "check https://example.com/page"
        entities, meta = extract_entities(prompt, None)
        assert "https://example.com/page" in entities
        assert meta["urls"] == 1

    def test_entities_extract_email_and_url(self):
        """Extract both email and URL"""
        prompt = "send https://example.com/doc to alice@test.com"
        entities, meta = extract_entities(prompt, None)
        assert "https://example.com/doc" in entities
        assert "alice@test.com" in entities
        assert meta["urls"] == 1
        assert meta["emails"] == 1

    def test_extract_capitalized_name(self):
        prompt = "contact John Smith about the project"
        entities, meta = extract_entities(prompt, None)
        assert "John Smith" in entities
        assert meta["names"] == 1

    def test_extract_multiple_names(self):
        prompt = "invite John Smith and Jane Doe to the meeting"
        entities, meta = extract_entities(prompt, None)
        assert "John Smith" in entities
        assert "Jane Doe" in entities
        assert meta["names"] == 2

    def test_extract_with_app(self):
        prompt = "send email"
        entities, meta = extract_entities(prompt, "gmail")
        assert "gmail" in entities
        assert "app_detection" in meta["methods"]

    def test_deduplication(self):
        """Entities should be deduplicated while preserving order"""
        prompt = "send test@example.com to test@example.com"
        entities, meta = extract_entities(prompt, None)
        assert entities.count("test@example.com") == 1
        assert len(entities) == 1

    def test_empty_prompt(self):
        entities, meta = extract_entities("", None)
        assert entities == []

    def test_no_entities(self):
        prompt = "hello world"
        entities, meta = extract_entities(prompt, None)
        assert entities == []


class TestPreprocessInput:
    """Integration tests for preprocess_input function"""

    def test_preprocess_send_email(self):
        state: GraphState = {
            "prompt": "  send email to john@example.com  ",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["normalized_prompt"] == "send email to john@example.com"
        assert result["task_type"] == TaskType.SEND_EMAIL.value
        assert "john@example.com" in result["entities"]
        assert "preprocess_meta" in result
        assert "matched_keywords" in result["preprocess_meta"]

    def test_preprocess_login_with_app(self):
        state: GraphState = {
            "prompt": "login to gmail with 2fa",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.LOGIN_AUTH.value
        assert result["app"] == "gmail"
        assert "gmail" in result["entities"]

    def test_preprocess_with_context(self):
        state: GraphState = {
            "prompt": "send email to team",
            "context": {"current_app": "outlook"},
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.SEND_EMAIL.value
        assert result["app"] == "outlook"

    def test_preprocess_chat(self):
        state: GraphState = {
            "prompt": "hello there",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.CHAT.value
        assert result["app"] is None

    def test_preprocess_unknown(self):
        state: GraphState = {
            "prompt": "this is a long unstructured prompt without any specific task indicators and it should be classified as unknown",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.UNKNOWN.value

    def test_preprocess_complex_prompt(self):
        state: GraphState = {
            "prompt": "login to gmail and send email to John Smith at john@example.com with attachment from https://example.com/doc.pdf",
            "context": None,
        }
        result = preprocess_input(state)

        # LOGIN_AUTH has highest priority
        assert result["task_type"] == TaskType.LOGIN_AUTH.value
        assert result["app"] == "gmail"

        # Should extract all entities
        entities = result["entities"]
        assert "john@example.com" in entities
        assert "https://example.com/doc.pdf" in entities
        assert "John Smith" in entities
        assert "gmail" in entities

    def test_preprocess_metadata(self):
        state: GraphState = {
            "prompt": "  test prompt  ",
            "context": None,
        }
        result = preprocess_input(state)

        meta = result["preprocess_meta"]
        assert "original_prompt" in meta
        assert "original_length" in meta
        assert "normalized_length" in meta
        assert "matched_keywords" in meta
        assert "extraction_meta" in meta

    def test_preprocess_empty_prompt(self):
        state: GraphState = {
            "prompt": "",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["normalized_prompt"] == ""
        assert result["task_type"] in [TaskType.CHAT.value, TaskType.UNKNOWN.value]
        assert result["entities"] == []

    def test_preprocess_fill_form_linkedin(self):
        state: GraphState = {
            "prompt": "fill out the linkedin job application form",
            "context": None,
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.FILL_FORM.value
        assert result["app"] == "linkedin"

    def test_preprocess_search_no_app(self):
        state: GraphState = {
            "prompt": "search for the latest AI news",
            "context": {"current_app": "gmail"},  # Gmail not compatible with search
        }
        result = preprocess_input(state)

        assert result["task_type"] == TaskType.SEARCH_BROWSE.value
        assert result["app"] is None  # Should not use incompatible context app


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
