"""
Unit tests for mem0_nodes.py and mem0_client.py

Tests cover:
- Router decision logic
- Mem0 loading with various response formats
- Error handling
- State caching
- Normalization edge cases
"""

import pytest
from mem0_nodes import (
    mem0_needed_router,
    load_mem0,
    use_mem0_state,
    GraphState,
    MEM0_ROUTE_LOAD,
    MEM0_ROUTE_USE,
)
from mem0_client import normalize_mem0_items, safe_str


# ============================================================================
# FAKE CLIENT FOR TESTING
# ============================================================================

class FakeMem0Client:
    """Fake mem0 client for testing"""

    def __init__(self, response_data=None, should_raise=False, raise_error=None):
        """
        Initialize fake client.

        Args:
            response_data: Data to return from get_all
            should_raise: If True, raise an exception
            raise_error: Specific error to raise
        """
        self.response_data = response_data
        self.should_raise = should_raise
        self.raise_error = raise_error or Exception("Test error")
        self.calls = []

    def get_all(self, user_id: str, filters=None):
        """Fake get_all implementation"""
        self.calls.append({"user_id": user_id, "filters": filters})

        if self.should_raise:
            raise self.raise_error

        return self.response_data

    def close(self):
        """Fake close"""
        pass


# ============================================================================
# TESTS: normalize_mem0_items
# ============================================================================

class TestNormalizeMem0Items:
    """Tests for normalize_mem0_items function"""

    def test_none_returns_empty_list(self):
        assert normalize_mem0_items(None) == []

    def test_empty_list_returns_empty_list(self):
        assert normalize_mem0_items([]) == []

    def test_list_of_dicts(self):
        data = [
            {"id": "1", "text": "memory 1"},
            {"id": "2", "text": "memory 2"},
        ]
        result = normalize_mem0_items(data)
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_list_of_strings(self):
        data = ["memory 1", "memory 2"]
        result = normalize_mem0_items(data)
        assert len(result) == 2
        assert result[0]["text"] == "memory 1"
        assert result[1]["text"] == "memory 2"

    def test_list_mixed_types(self):
        data = [
            {"id": "1", "text": "dict memory"},
            "string memory",
            None,  # Should be ignored
            123,  # Should be ignored
            {"id": "2"},
        ]
        result = normalize_mem0_items(data)
        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[1]["text"] == "string memory"
        assert result[2]["id"] == "2"

    def test_dict_with_memories_key(self):
        data = {
            "memories": [
                {"id": "1", "text": "memory 1"},
                {"id": "2", "text": "memory 2"},
            ]
        }
        result = normalize_mem0_items(data)
        assert len(result) == 2
        assert result[0]["id"] == "1"

    def test_dict_with_items_key(self):
        data = {
            "items": [
                {"id": "1", "text": "item 1"},
            ]
        }
        result = normalize_mem0_items(data)
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_dict_with_results_key(self):
        data = {
            "results": [{"id": "1"}]
        }
        result = normalize_mem0_items(data)
        assert len(result) == 1

    def test_dict_with_data_key(self):
        data = {
            "data": [{"id": "1"}]
        }
        result = normalize_mem0_items(data)
        assert len(result) == 1

    def test_dict_single_memory_object_with_text(self):
        data = {"id": "1", "text": "single memory"}
        result = normalize_mem0_items(data)
        assert len(result) == 1
        assert result[0]["text"] == "single memory"

    def test_dict_single_memory_object_with_content(self):
        data = {"id": "1", "content": "memory content"}
        result = normalize_mem0_items(data)
        assert len(result) == 1
        assert result[0]["content"] == "memory content"

    def test_dict_single_memory_object_with_memory(self):
        data = {"memory": "memory text", "id": "1"}
        result = normalize_mem0_items(data)
        assert len(result) == 1

    def test_dict_single_memory_object_with_message(self):
        data = {"message": "message text", "id": "1"}
        result = normalize_mem0_items(data)
        assert len(result) == 1

    def test_dict_unrecognized_structure(self):
        data = {"foo": "bar", "baz": 123}
        result = normalize_mem0_items(data)
        assert result == []

    def test_empty_dict(self):
        assert normalize_mem0_items({}) == []

    def test_string_returns_empty(self):
        assert normalize_mem0_items("not a valid structure") == []

    def test_number_returns_empty(self):
        assert normalize_mem0_items(123) == []

    def test_list_with_empty_strings_ignored(self):
        data = ["valid", "", "  ", "also valid"]
        result = normalize_mem0_items(data)
        assert len(result) == 2
        assert result[0]["text"] == "valid"
        assert result[1]["text"] == "also valid"


class TestSafeStr:
    """Tests for safe_str helper"""

    def test_normal_string(self):
        assert safe_str("hello") == "hello"

    def test_long_string_truncated(self):
        long_str = "a" * 300
        result = safe_str(long_str, max_length=200)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_none(self):
        result = safe_str(None)
        assert "None" in result

    def test_dict(self):
        result = safe_str({"key": "value"})
        assert "key" in result


# ============================================================================
# TESTS: mem0_needed_router
# ============================================================================

class TestMem0NeededRouter:
    """Tests for mem0_needed_router"""

    def test_force_reload_true_returns_load(self):
        state: GraphState = {
            "force_reload_mem0": True,
            "mem0_state": {"items": [{"id": "1"}]},  # Even with valid cache
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_LOAD

    def test_missing_mem0_state_returns_load(self):
        state: GraphState = {
            "force_reload_mem0": False,
            "mem0_state": None,
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_LOAD

    def test_mem0_state_without_items_returns_load(self):
        state: GraphState = {
            "force_reload_mem0": False,
            "mem0_state": {"raw": "something"},  # Missing "items" key
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_LOAD

    def test_valid_mem0_state_returns_use(self):
        state: GraphState = {
            "force_reload_mem0": False,
            "mem0_state": {
                "items": [{"id": "1", "text": "memory"}],
                "raw": [...],
                "summary": {"count": 1},
            },
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_USE

    def test_empty_items_list_is_valid_returns_use(self):
        """Empty items list is a valid state (no memories)"""
        state: GraphState = {
            "force_reload_mem0": False,
            "mem0_state": {
                "items": [],
                "raw": None,
                "summary": {"count": 0},
            },
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_USE

    def test_no_force_reload_flag_defaults_false(self):
        """If force_reload_mem0 is not in state, default to False"""
        state: GraphState = {
            "mem0_state": {"items": []},
        }
        assert mem0_needed_router(state) == MEM0_ROUTE_USE


# ============================================================================
# TESTS: load_mem0
# ============================================================================

class TestLoadMem0:
    """Tests for load_mem0 node"""

    def test_missing_user_id_returns_error(self):
        state: GraphState = {}
        result = load_mem0(state)

        assert result["mem0_error"] is not None
        assert "user_id" in result["mem0_error"]
        assert result["mem0_loaded"] is False
        assert result["mem0_items"] == []

    def test_success_list_data(self):
        """Test successful load with data as list"""
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "message": "ok",
                "data": [
                    {"id": "1", "text": "memory 1"},
                    {"id": "2", "text": "memory 2"},
                ]
            }
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is None
        assert result["mem0_loaded"] is True
        assert len(result["mem0_items"]) == 2
        assert result["mem0_items"][0]["id"] == "1"

        # Check mem0_state structure
        assert "items" in result["mem0_state"]
        assert "raw" in result["mem0_state"]
        assert "summary" in result["mem0_state"]
        assert result["mem0_state"]["summary"]["count"] == 2

    def test_success_dict_with_memories_key(self):
        """Test successful load with data as dict with 'memories' key"""
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "message": "ok",
                "data": {
                    "memories": [
                        {"id": "1", "text": "memory 1"},
                    ]
                }
            }
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is None
        assert result["mem0_loaded"] is True
        assert len(result["mem0_items"]) == 1
        assert result["mem0_items"][0]["id"] == "1"

    def test_success_false_sets_mem0_error(self):
        """Test that success=False in response sets error"""
        fake_client = FakeMem0Client(
            response_data={
                "success": False,
                "message": "API error: rate limit exceeded",
                "data": None,
            }
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is not None
        assert "rate limit exceeded" in result["mem0_error"]
        assert result["mem0_loaded"] is False
        assert result["mem0_items"] == []

    def test_exception_sets_mem0_error(self):
        """Test that exceptions are caught and set error"""
        fake_client = FakeMem0Client(
            should_raise=True,
            raise_error=Exception("Connection timeout")
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is not None
        assert "Exception loading mem0" in result["mem0_error"]
        assert "Connection timeout" in result["mem0_error"]
        assert result["mem0_loaded"] is False
        assert result["mem0_items"] == []

    def test_empty_data_returns_empty_items(self):
        """Test that empty data returns empty items (not an error)"""
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "message": "ok",
                "data": []
            }
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is None
        assert result["mem0_loaded"] is True
        assert result["mem0_items"] == []
        assert result["mem0_state"]["summary"]["count"] == 0

    def test_normalizes_string_items(self):
        """Test that string items in list are normalized"""
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "message": "ok",
                "data": ["memory text 1", "memory text 2"]
            }
        )

        state: GraphState = {"user_id": "test_user"}
        result = load_mem0(state, client=fake_client)

        assert result["mem0_error"] is None
        assert len(result["mem0_items"]) == 2
        assert result["mem0_items"][0]["text"] == "memory text 1"
        assert result["mem0_items"][1]["text"] == "memory text 2"

    def test_client_receives_user_id(self):
        """Test that client is called with correct user_id"""
        fake_client = FakeMem0Client(
            response_data={"success": True, "data": []}
        )

        state: GraphState = {"user_id": "my_user_123"}
        load_mem0(state, client=fake_client)

        assert len(fake_client.calls) == 1
        assert fake_client.calls[0]["user_id"] == "my_user_123"


# ============================================================================
# TESTS: use_mem0_state
# ============================================================================

class TestUseMem0State:
    """Tests for use_mem0_state node"""

    def test_extracts_items_from_cached_state(self):
        state: GraphState = {
            "mem0_state": {
                "items": [
                    {"id": "1", "text": "cached memory 1"},
                    {"id": "2", "text": "cached memory 2"},
                ],
                "raw": [...],
                "summary": {"count": 2},
            }
        }

        result = use_mem0_state(state)

        assert result["mem0_error"] is None
        assert result["mem0_loaded"] is False  # Using cache, not loaded
        assert len(result["mem0_items"]) == 2
        assert result["mem0_items"][0]["id"] == "1"

    def test_empty_items_list(self):
        state: GraphState = {
            "mem0_state": {
                "items": [],
                "raw": None,
                "summary": {"count": 0},
            }
        }

        result = use_mem0_state(state)

        assert result["mem0_error"] is None
        assert result["mem0_loaded"] is False
        assert result["mem0_items"] == []

    def test_missing_mem0_state_sets_error(self):
        """If mem0_state is None, should handle gracefully"""
        state: GraphState = {
            "mem0_state": None,
        }

        result = use_mem0_state(state)

        assert result["mem0_error"] is not None
        assert "mem0_state is None" in result["mem0_error"]
        assert result["mem0_loaded"] is False
        assert result["mem0_items"] == []

    def test_mem0_state_missing_items_key(self):
        """If mem0_state exists but missing items key"""
        state: GraphState = {
            "mem0_state": {
                "raw": "something",
                "summary": {},
            }
        }

        result = use_mem0_state(state)

        assert result["mem0_error"] is None
        assert result["mem0_items"] == []  # Defaults to empty list


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMem0Integration:
    """Integration tests for the full mem0 flow"""

    def test_full_flow_force_reload(self):
        """Test complete flow with force_reload=True"""
        # Initial state
        state: GraphState = {
            "user_id": "test_user",
            "force_reload_mem0": True,
            "mem0_state": {"items": [{"id": "old"}]},  # Old cache
        }

        # Router should choose LOAD
        route = mem0_needed_router(state)
        assert route == MEM0_ROUTE_LOAD

        # Load new data
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "data": [{"id": "new", "text": "new memory"}]
            }
        )
        result = load_mem0(state, client=fake_client)

        assert result["mem0_loaded"] is True
        assert len(result["mem0_items"]) == 1
        assert result["mem0_items"][0]["id"] == "new"

    def test_full_flow_use_cache(self):
        """Test complete flow using cached state"""
        # State with valid cache
        state: GraphState = {
            "user_id": "test_user",
            "force_reload_mem0": False,
            "mem0_state": {
                "items": [{"id": "cached", "text": "cached memory"}],
                "raw": [...],
                "summary": {"count": 1},
            },
        }

        # Router should choose USE
        route = mem0_needed_router(state)
        assert route == MEM0_ROUTE_USE

        # Use cached data
        result = use_mem0_state(state)

        assert result["mem0_loaded"] is False  # Not loaded, using cache
        assert len(result["mem0_items"]) == 1
        assert result["mem0_items"][0]["id"] == "cached"

    def test_full_flow_first_load(self):
        """Test complete flow on first load (no cache)"""
        # State without cache
        state: GraphState = {
            "user_id": "test_user",
            "force_reload_mem0": False,
            "mem0_state": None,
        }

        # Router should choose LOAD
        route = mem0_needed_router(state)
        assert route == MEM0_ROUTE_LOAD

        # Load data
        fake_client = FakeMem0Client(
            response_data={
                "success": True,
                "data": [{"id": "1", "text": "first memory"}]
            }
        )
        result = load_mem0(state, client=fake_client)

        assert result["mem0_loaded"] is True
        assert len(result["mem0_items"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
