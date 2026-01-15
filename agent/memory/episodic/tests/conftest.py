"""
Shared Test Fixtures and Mocks

Provides mock clients, database fixtures, and factory functions
for testing the memory system without external dependencies.
"""

import os
import sys
import tempfile
import hashlib
import pytest
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# Mock Clients
# =============================================================================

class FakeMem0Client:
    """
    Fake mem0 client for testing.

    Tracks all calls and returns configurable responses.
    """

    def __init__(self, responses: Dict[str, Any] = None, should_fail: bool = False):
        self.responses = responses or {}
        self.should_fail = should_fail
        self.calls: List[tuple] = []

    def get_all(self, user_id: str, filters: Dict = None) -> Dict[str, Any]:
        self.calls.append(("get_all", user_id, filters))
        if self.should_fail:
            return {"success": False, "message": "Mock error"}
        return self.responses.get("get_all", {"success": True, "data": []})

    def search(self, user_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        self.calls.append(("search", user_id, query, limit))
        if self.should_fail:
            return {"success": False, "message": "Mock error"}
        return self.responses.get("search", {"success": True, "data": []})

    def add(self, user_id: str, text: str, metadata: Dict = None) -> Dict[str, Any]:
        self.calls.append(("add", user_id, text, metadata))
        if self.should_fail:
            return {"success": False, "message": "Mock error"}
        return self.responses.get("add", {"success": True, "data": {"id": "mock-mem0-id"}})

    def add_messages(self, user_id: str, messages: list, metadata: Dict = None) -> Dict[str, Any]:
        self.calls.append(("add_messages", user_id, messages, metadata))
        if self.should_fail:
            return {"success": False, "message": "Mock error"}
        return self.responses.get("add_messages", {"success": True, "data": {"id": "mock-mem0-id"}})

    def health_check(self) -> bool:
        return not self.should_fail

    def close(self):
        pass


class FakeEmbeddingClient:
    """
    Fake embedding client for testing.

    Returns deterministic embeddings based on text hash.
    """

    def __init__(self, dimension: int = 768, should_fail: bool = False):
        self.dimension = dimension
        self.should_fail = should_fail
        self.calls: List[str] = []

    def embed(self, text: str) -> Optional[List[float]]:
        self.calls.append(text)
        if self.should_fail:
            return None

        # Deterministic embedding based on text hash
        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(h >> i) % 100 / 100.0 for i in range(self.dimension)]

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        return [self.embed(text) for text in texts]

    def health_check(self) -> bool:
        return not self.should_fail

    def close(self):
        pass


class FakeKafkaClient:
    """
    Fake Kafka client for testing.

    Tracks sent messages and returns configurable responses.
    """

    def __init__(self, responses: Dict[str, Dict] = None):
        self.sent_messages: List[tuple] = []
        self.responses = responses or {}
        self._message_counter = 0

    def send_approval_request(self, proposal: Dict, timeout_seconds: int = 300) -> str:
        msg_id = f"mock-msg-{self._message_counter}"
        self._message_counter += 1
        self.sent_messages.append((msg_id, proposal, timeout_seconds))
        return msg_id

    def wait_for_response(self, message_id: str, timeout_seconds: int = 300) -> Optional[Dict]:
        return self.responses.get(message_id, None)

    def consume(self, topic: str, timeout_ms: int = 1000, max_records: int = 10) -> list:
        return self.responses.get(f"consume_{topic}", [])

    def get_pending_count(self) -> int:
        return len(self.sent_messages)

    def cleanup_expired(self) -> int:
        return 0

    def close(self):
        pass


class FakeLLMClient:
    """
    Fake LLM client for testing.

    Returns configurable responses.
    """

    def __init__(self, response: str = "Mock LLM response", memory_intents: Dict = None):
        self.response = response
        self.memory_intents = memory_intents
        self.calls: List[Dict] = []

    def generate(self, context: Dict[str, Any]) -> tuple:
        self.calls.append(context)
        return self.response, self.memory_intents


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def temp_db():
    """
    Create a temporary SQLite database for testing.

    Yields the EpisodeRepository instance, then cleans up.
    """
    from app.storage.episode_repository import EpisodeRepository

    # Create temp file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize repository (creates schema)
    repo = EpisodeRepository(db_path)

    yield repo

    # Cleanup
    repo.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def temp_db_path():
    """
    Create a temporary database path without initializing.

    Useful when you need to control initialization.
    """
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass


# =============================================================================
# Factory Fixtures
# =============================================================================

@pytest.fixture
def sample_episode():
    """
    Factory fixture for creating test episodes.

    Usage:
        episode = sample_episode(user_id="test", text="hello")
    """
    def _make(
        user_id: str = "test_user",
        text: str = "test content",
        fingerprint: str = None,
        **kwargs
    ):
        from app.storage.episode_schema import Episode
        from app.storage.fingerprint import generate_fingerprint

        # Generate fingerprint if not provided
        if fingerprint is None:
            fingerprint = generate_fingerprint(
                episode_type=kwargs.get("episode_type", "interaction"),
                task_type=kwargs.get("task_type"),
                app=kwargs.get("app"),
                entities=kwargs.get("entities", []),
                summary=kwargs.get("summary"),
                text=text
            )

        return Episode(
            user_id=user_id,
            fingerprint=fingerprint,
            text=text,
            summary=kwargs.get("summary"),
            episode_type=kwargs.get("episode_type", "interaction"),
            task_type=kwargs.get("task_type"),
            app=kwargs.get("app"),
            entities=kwargs.get("entities", []),
            embedding=kwargs.get("embedding"),
            embedding_model=kwargs.get("embedding_model"),
            importance_score=kwargs.get("importance_score", 0.5),
            confidence=kwargs.get("confidence", 0.8),
            reinforcement_count=kwargs.get("reinforcement_count", 1),
            is_deleted=kwargs.get("is_deleted", False),
            promoted_to_mem0=kwargs.get("promoted_to_mem0", False),
            promotion_proposal_id=kwargs.get("promotion_proposal_id"),
        )

    return _make


@pytest.fixture
def sample_proposal():
    """
    Factory fixture for creating test promotion proposals.
    """
    def _make(
        user_id: str = "test_user",
        episode_id: str = "test-episode-id",
        **kwargs
    ):
        from app.storage.episode_schema import PromotionProposal

        now = datetime.utcnow()
        return PromotionProposal(
            episode_id=episode_id,
            user_id=user_id,
            target_path=kwargs.get("target_path", "patterns.test"),
            proposed_value=kwargs.get("proposed_value", "Test proposed value"),
            confidence=kwargs.get("confidence", 0.8),
            evidence=kwargs.get("evidence", [episode_id]),
            status=kwargs.get("status", "pending"),
            created_at=kwargs.get("created_at", now),
            expires_at=kwargs.get("expires_at", now + timedelta(minutes=5)),
        )

    return _make


# =============================================================================
# Mock Client Fixtures
# =============================================================================

@pytest.fixture
def fake_mem0():
    """Provide a fake mem0 client."""
    return FakeMem0Client()


@pytest.fixture
def fake_embeddings():
    """Provide a fake embedding client."""
    return FakeEmbeddingClient()


@pytest.fixture
def fake_kafka():
    """Provide a fake Kafka client."""
    return FakeKafkaClient()


@pytest.fixture
def fake_llm():
    """Provide a fake LLM client."""
    return FakeLLMClient()


# =============================================================================
# Patching Fixtures
# =============================================================================

@pytest.fixture
def mock_mem0_client(fake_mem0):
    """
    Patch the mem0 client globally.

    Patches all locations where get_mem0_client is imported and used.

    Usage in test:
        def test_something(mock_mem0_client):
            # mem0 is now mocked
            pass
    """
    # Need to patch where the function is USED, not where it's DEFINED
    # (Python's from X import Y creates a local binding)
    patches = [
        patch('app.clients.mem0_client.get_mem0_client', return_value=fake_mem0),
        patch('app.graphs.user_approval_graph.nodes.apply_mem0_patch.get_mem0_client', return_value=fake_mem0),
        patch('app.graphs.main_graph.nodes.load_mem0.node.get_mem0_client', return_value=fake_mem0),
        patch('app.graphs.main_graph.nodes.retrieve_episodes.node.get_mem0_client', return_value=fake_mem0),
    ]

    for p in patches:
        p.start()

    yield fake_mem0

    for p in patches:
        p.stop()


@pytest.fixture
def mock_embedding_client(fake_embeddings):
    """Patch the embedding client globally."""
    with patch('app.clients.ollama_embeddings.get_embedding_client', return_value=fake_embeddings):
        yield fake_embeddings


@pytest.fixture
def mock_kafka_client(fake_kafka):
    """Patch the Kafka client globally."""
    with patch('app.clients.kafka_client.get_kafka_client', return_value=fake_kafka):
        yield fake_kafka


@pytest.fixture
def mock_repository(temp_db):
    """
    Patch the episode repository globally.

    Patches all locations where get_episode_repository is imported and used.
    Uses create=True to handle modules that import inside functions.
    """
    # Need to patch where the function is USED, not where it's DEFINED
    # Use create=True to create the attribute if it doesn't exist (for late imports)
    patches = [
        patch('app.storage.get_episode_repository', return_value=temp_db),
        patch('app.graphs.user_approval_graph.nodes.apply_mem0_patch.get_episode_repository', return_value=temp_db),
        patch('app.graphs.user_approval_graph.nodes.record_decision.get_episode_repository', return_value=temp_db),
        patch('app.graphs.memory_write_graph.nodes.dedupe_lookup.get_episode_repository', return_value=temp_db),
        patch('app.graphs.memory_write_graph.nodes.insert_episode.get_episode_repository', return_value=temp_db),
        patch('app.graphs.memory_write_graph.nodes.reinforce_episode.get_episode_repository', return_value=temp_db),
        patch('app.graphs.memory_write_graph.nodes.embed_episode.get_episode_repository', return_value=temp_db),
        patch('app.graphs.memory_write_graph.nodes.create_promotion_proposal.get_episode_repository', return_value=temp_db),
        patch('app.graphs.reflection_graph.nodes.load_recent_episodes.get_episode_repository', return_value=temp_db),
        patch('app.graphs.reflection_graph.nodes.resolve_conflicts.get_episode_repository', return_value=temp_db),
        patch('app.graphs.reflection_graph.nodes.create_promotion_proposals.get_episode_repository', return_value=temp_db),
    ]

    for p in patches:
        p.start()

    yield temp_db

    for p in patches:
        p.stop()


# =============================================================================
# Test Data
# =============================================================================

@pytest.fixture
def sample_memory_write_state():
    """Sample state for memory_write_graph tests."""
    return {
        "user_id": "test_user",
        "prompt": "send email to john@example.com about the meeting",
        "llm_output": "I'll send that email to John about the meeting.",
        "task_type": "email",
        "app": "mail",
        "entities": ["john@example.com", "meeting"],
        "memory_intents": None,
        "importance_score": 0.6,
        "timestamp": datetime.utcnow().isoformat(),
        "errors": []
    }


@pytest.fixture
def sample_reflection_state():
    """Sample state for reflection_graph tests."""
    return {
        "user_id": "test_user",
        "lookback_days": 7,
        "errors": []
    }


@pytest.fixture
def sample_approval_state(sample_proposal):
    """Sample state for user_approval_graph tests."""
    proposal = sample_proposal()
    return {
        "proposal": proposal.model_dump(),
        "proposal_id": proposal.id,
        "episode_id": proposal.episode_id,
        "user_id": proposal.user_id,
        "errors": []
    }


# =============================================================================
# Utility Functions
# =============================================================================

def create_episodes_with_same_fingerprint(repo, sample_episode, count: int = 3):
    """
    Helper to create multiple episodes with the same fingerprint.

    Useful for testing reinforcement and pattern detection.
    """
    episodes = []
    fingerprint = "test-fingerprint-" + hashlib.md5(b"test").hexdigest()[:16]

    for i in range(count):
        episode = sample_episode(
            user_id="test_user",
            text=f"Test content {i}",
            fingerprint=fingerprint,
            reinforcement_count=1
        )
        repo.insert_episode(episode)
        episodes.append(episode)

    return episodes, fingerprint


def assert_episode_in_db(repo, episode_id: str):
    """Assert that an episode exists in the database."""
    episode = repo.get_episode_by_id(episode_id)
    assert episode is not None, f"Episode {episode_id} not found in database"
    return episode


def assert_proposal_in_db(repo, proposal_id: str):
    """Assert that a proposal exists in the database."""
    proposal = repo.get_proposal(proposal_id)
    assert proposal is not None, f"Proposal {proposal_id} not found in database"
    return proposal
