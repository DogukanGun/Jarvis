"""Tests for Router Graph."""
import pytest
from unittest.mock import patch, MagicMock

from app.graphs.router_graph.nodes.validate_request import validate_request_node
from app.graphs.router_graph.nodes.route_request import route_request_node, route_decision
from app.graphs.router_graph.state import RouterGraphState


class TestValidateRequestNode:
    """Tests for validate_request node."""

    def test_valid_image_request(self, sample_image_request):
        """Test validation of valid image request."""
        state: RouterGraphState = {
            "raw_message": sample_image_request,
        }

        result = validate_request_node(state)

        assert result["is_valid"] is True
        assert result["validation_errors"] == []
        assert result["request"] is not None
        assert result["job_id"] == "test-job-123"

    def test_valid_video_request(self, sample_video_request):
        """Test validation of valid video request."""
        state: RouterGraphState = {
            "raw_message": sample_video_request,
        }

        result = validate_request_node(state)

        assert result["is_valid"] is True
        assert result["validation_errors"] == []

    def test_invalid_missing_prompt(self):
        """Test validation fails for missing prompt."""
        state: RouterGraphState = {
            "raw_message": {
                "job_id": "test-123",
                "task": "image_from_prompt",
            },
        }

        result = validate_request_node(state)

        assert result["is_valid"] is False
        assert len(result["validation_errors"]) > 0

    def test_invalid_video_without_duration(self):
        """Test video request without duration fails."""
        state: RouterGraphState = {
            "raw_message": {
                "job_id": "test-123",
                "task": "video_from_prompt",
                "prompt": "test video",
                "output": {"format": "mp4"},
            },
        }

        result = validate_request_node(state)

        assert result["is_valid"] is False
        assert any("duration" in err.lower() for err in result["validation_errors"])

    def test_invalid_edit_without_image_url(self):
        """Test edit request without input_image_url fails."""
        state: RouterGraphState = {
            "raw_message": {
                "job_id": "test-123",
                "task": "edit_image_from_prompt_and_image",
                "prompt": "edit this",
            },
        }

        result = validate_request_node(state)

        assert result["is_valid"] is False
        assert any("input_image_url" in err for err in result["validation_errors"])


class TestRouteRequestNode:
    """Tests for route_request node."""

    def test_route_valid_request(self, sample_image_request):
        """Test routing valid request."""
        from app.schemas.messages import RenderRequest

        state: RouterGraphState = {
            "is_valid": True,
            "request": sample_image_request,
        }

        result = route_request_node(state)

        assert result["routing_decision"] == "route"
        assert result["target_topic"] is not None
        assert "image.prompt" in result["target_topic"]

    def test_reject_invalid_request(self):
        """Test rejecting invalid request."""
        state: RouterGraphState = {
            "is_valid": False,
            "validation_errors": ["Some error"],
        }

        result = route_request_node(state)

        assert result["routing_decision"] == "reject"
        assert result["target_topic"] is None


class TestRouteDecision:
    """Tests for route_decision edge function."""

    def test_decision_publish(self):
        """Test decision to publish."""
        state: RouterGraphState = {
            "routing_decision": "route",
            "target_topic": "media.render.image.prompt.requests",
        }

        result = route_decision(state)
        assert result == "publish"

    def test_decision_error(self):
        """Test decision for error."""
        state: RouterGraphState = {
            "routing_decision": "reject",
            "target_topic": None,
        }

        result = route_decision(state)
        assert result == "error"
