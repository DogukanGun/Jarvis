"""Integration tests for end-to-end pipeline."""
import pytest
from unittest.mock import patch, MagicMock


class TestRouterIntegration:
    """Integration tests for the router graph."""

    @patch("app.clients.kafka_client.client.get_kafka_client")
    def test_router_graph_valid_request(self, mock_get_kafka, sample_image_request):
        """Test router graph processes valid request."""
        from app.graphs.router_graph import run_router_graph

        # Setup mock
        mock_kafka = MagicMock()
        mock_kafka.publish.return_value = True
        mock_get_kafka.return_value = mock_kafka

        # Run graph
        result = run_router_graph(sample_image_request)

        # Verify
        assert result["is_valid"] is True
        assert result["routing_decision"] == "route"
        assert result["publish_success"] is True

        # Verify publish was called
        mock_kafka.publish.assert_called()
        call_args = mock_kafka.publish.call_args
        assert "image.prompt" in call_args.kwargs["topic"]

    @patch("app.clients.kafka_client.client.get_kafka_client")
    def test_router_graph_invalid_request(self, mock_get_kafka):
        """Test router graph handles invalid request."""
        from app.graphs.router_graph import run_router_graph

        mock_kafka = MagicMock()
        mock_kafka.publish.return_value = True
        mock_get_kafka.return_value = mock_kafka

        # Invalid request - missing prompt
        invalid_request = {
            "job_id": "test-123",
            "task": "image_from_prompt",
        }

        result = run_router_graph(invalid_request)

        # Verify error result was published
        assert result["is_valid"] is False
        assert result["routing_decision"] == "reject"

        # Check error was published to results topic
        mock_kafka.publish.assert_called()
        call_args = mock_kafka.publish.call_args
        assert "results" in call_args.kwargs["topic"]


class TestImagePromptIntegration:
    """Integration tests for image prompt graph (mocked model)."""

    @patch("app.clients.kafka_client.client.get_kafka_client")
    @patch("app.clients.storage_client.client.get_storage_client")
    @patch("app.clients.model_client.client.get_image_model")
    def test_image_prompt_graph_success(
        self,
        mock_get_model,
        mock_get_storage,
        mock_get_kafka,
        sample_image_request,
        mock_kafka_client,
        mock_storage_client,
        mock_image_model,
    ):
        """Test image prompt graph generates image successfully."""
        from app.graphs.image_prompt_graph import run_image_prompt_graph

        # Setup mocks
        mock_get_kafka.return_value = mock_kafka_client
        mock_get_storage.return_value = mock_storage_client
        mock_get_model.return_value = mock_image_model

        # Run graph
        result = run_image_prompt_graph(sample_image_request)

        # Verify
        assert result["model_loaded"] is True
        assert result["generation_success"] is True
        assert result["upload_success"] is True
        assert result["result_published"] is True
        assert result["response_url"] is not None

    @patch("app.clients.kafka_client.client.get_kafka_client")
    @patch("app.clients.model_client.client.get_image_model")
    def test_image_prompt_graph_model_error(
        self,
        mock_get_model,
        mock_get_kafka,
        sample_image_request,
        mock_kafka_client,
    ):
        """Test image prompt graph handles model error."""
        from app.graphs.image_prompt_graph import run_image_prompt_graph

        # Setup mocks - model fails to load
        mock_get_kafka.return_value = mock_kafka_client
        mock_get_model.side_effect = RuntimeError("CUDA out of memory")

        # Run graph
        result = run_image_prompt_graph(sample_image_request)

        # Verify error handling
        assert result["model_loaded"] is False
        assert "error" in result
        assert result["result_published"] is True  # Error was published


class TestVideoIntegration:
    """Integration tests for video graph (mocked model)."""

    @patch("app.clients.kafka_client.client.get_kafka_client")
    @patch("app.clients.storage_client.client.get_storage_client")
    @patch("app.clients.model_client.client.get_video_model")
    def test_video_graph_success(
        self,
        mock_get_model,
        mock_get_storage,
        mock_get_kafka,
        sample_video_request,
        mock_kafka_client,
        mock_storage_client,
    ):
        """Test video graph generates video successfully."""
        from app.graphs.video_graph import run_video_graph
        from PIL import Image
        import numpy as np

        # Setup mocks
        mock_get_kafka.return_value = mock_kafka_client
        mock_get_storage.return_value = mock_storage_client

        # Mock video model result
        mock_model = MagicMock()
        fake_frames = [
            Image.fromarray(np.random.randint(0, 255, (384, 512, 3), dtype=np.uint8))
            for _ in range(10)
        ]
        mock_result = MagicMock()
        mock_result.frames = [fake_frames]
        mock_model.return_value = mock_result
        mock_get_model.return_value = mock_model

        # Run graph
        result = run_video_graph(sample_video_request)

        # Verify
        assert result["model_loaded"] is True
        assert result["generation_success"] is True
        # encode_video and upload may or may not succeed depending on ffmpeg availability
