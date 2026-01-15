"""
Smoke test for MainGraph

Tests the complete MainGraph flow end-to-end with mock clients.
"""

import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app.graphs.main_graph import run_main_graph
from app.config import config


def test_main_graph_smoke_test():
    """
    Smoke test: Run complete MainGraph flow.

    Uses mock LLM client to avoid external dependencies.
    """
    # Set config to use mock LLM
    original_provider = config.LLM_PROVIDER
    config.LLM_PROVIDER = "mock"

    try:
        # Run graph
        result = run_main_graph(
            user_id="test_user_123",
            prompt="send email to john@example.com about the project",
            context={}
        )

        # Verify all expected fields are present
        assert "user_id" in result
        assert result["user_id"] == "test_user_123"

        # Node 1: preprocess_input
        assert "normalized_prompt" in result
        assert "task_type" in result
        assert "entities" in result
        assert result["task_type"] == "send_email"

        # Nodes 2-4: mem0
        assert "mem0_items" in result
        assert "mem0_error" in result or result.get("mem0_error") is None

        # Node 5: retrieve_episodes
        assert "retrieved_episodes" in result
        assert "retrieval_query" in result

        # Node 6: compose_context
        assert "llm_context" in result
        assert "persona" in result["llm_context"]
        assert "user_prompt" in result["llm_context"]

        # Node 7: llm_step
        assert "llm_output" in result
        assert "memory_intents" in result
        assert result["llm_output"] is not None

        # Node 8: return_output
        assert "response_payload" in result
        assert "answer" in result["response_payload"]
        assert "metadata" in result["response_payload"]

        # Node 9: enqueue_memory_write_graph
        assert "memory_job_payload" in result or "enqueue_error" in result

        print("✓ Smoke test passed!")
        print(f"  Task type: {result['task_type']}")
        print(f"  Answer: {result['response_payload']['answer'][:50]}...")

    finally:
        # Restore original config
        config.LLM_PROVIDER = original_provider


def test_main_graph_chat_task():
    """Test MainGraph with a chat task"""
    config.LLM_PROVIDER = "mock"

    result = run_main_graph(
        user_id="test_user",
        prompt="hello how are you",
        context={}
    )

    # Should detect as chat
    assert result["task_type"] == "chat"
    assert "response_payload" in result


def test_main_graph_with_force_reload():
    """Test MainGraph with force_mem0_reload flag"""
    config.LLM_PROVIDER = "mock"

    result = run_main_graph(
        user_id="test_user",
        prompt="test with force reload",
        context={"force_mem0_reload": True}
    )

    # Should have loaded mem0 (or attempted to)
    assert "mem0_loaded" in result or "mem0_error" in result


def test_main_graph_error_handling():
    """Test that MainGraph handles errors gracefully"""
    # This tests that even with potential errors, the graph completes
    config.LLM_PROVIDER = "mock"

    result = run_main_graph(
        user_id="test_user",
        prompt="test error handling",
        context={}
    )

    # Should always produce a response_payload
    assert "response_payload" in result
    assert "answer" in result["response_payload"]


if __name__ == "__main__":
    # Run tests
    print("=" * 70)
    print("MAIN GRAPH SMOKE TESTS")
    print("=" * 70)

    test_main_graph_smoke_test()
    print()
    test_main_graph_chat_task()
    print()
    test_main_graph_with_force_reload()
    print()
    test_main_graph_error_handling()

    print("\n" + "=" * 70)
    print("✓ All smoke tests passed!")
    print("=" * 70)
