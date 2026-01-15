"""
Demo script for mem0 nodes

Shows how the mem0 router and loading nodes work with various scenarios.
Uses fake client to avoid actual API calls.
"""

from mem0_nodes import (
    mem0_needed_router,
    load_mem0,
    use_mem0_state,
    GraphState,
    MEM0_ROUTE_LOAD,
    MEM0_ROUTE_USE,
)
from test_mem0_nodes import FakeMem0Client


def print_separator(title=""):
    """Print a visual separator"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)
    else:
        print()


def demo_scenario(title, state, client=None, show_use_state=False):
    """Run a demo scenario"""
    print_separator(title)

    # Show initial state
    print("Initial State:")
    print(f"  user_id: {state.get('user_id', 'N/A')}")
    print(f"  force_reload_mem0: {state.get('force_reload_mem0', False)}")
    print(f"  mem0_state: {'Present' if state.get('mem0_state') else 'None'}")

    # Router decision
    route = mem0_needed_router(state)
    print(f"\nRouter Decision: {route}")

    # Execute based on route
    if route == MEM0_ROUTE_LOAD:
        print("\nExecuting: load_mem0()")
        result = load_mem0(state, client=client)

        print(f"  mem0_loaded: {result['mem0_loaded']}")
        print(f"  mem0_error: {result['mem0_error']}")
        print(f"  mem0_items count: {len(result['mem0_items'])}")

        if result['mem0_items']:
            print(f"  First item: {result['mem0_items'][0]}")

    else:  # MEM0_ROUTE_USE
        print("\nExecuting: use_mem0_state()")
        result = use_mem0_state(state)

        print(f"  mem0_loaded: {result['mem0_loaded']} (using cache)")
        print(f"  mem0_error: {result['mem0_error']}")
        print(f"  mem0_items count: {len(result['mem0_items'])}")

        if result['mem0_items']:
            print(f"  First item: {result['mem0_items'][0]}")


def main():
    """Run demo scenarios"""
    print_separator("JARVIS MEM0 NODES DEMO")
    print("Nodes 2-4: mem0_needed (router), load_mem0, use_mem0_state")
    print_separator()

    # ========================================================================
    # Scenario 1: First load (no cache)
    # ========================================================================
    fake_client_1 = FakeMem0Client(
        response_data={
            "success": True,
            "message": "ok",
            "data": [
                {"id": "1", "text": "User prefers dark mode"},
                {"id": "2", "text": "User is a Python developer"},
                {"id": "3", "text": "User works at TechCorp"},
            ]
        }
    )

    state_1: GraphState = {
        "user_id": "user_123",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 1: First Load (No Cache)",
        state_1,
        client=fake_client_1
    )

    # ========================================================================
    # Scenario 2: Using cached state
    # ========================================================================
    state_2: GraphState = {
        "user_id": "user_123",
        "force_reload_mem0": False,
        "mem0_state": {
            "items": [
                {"id": "c1", "text": "Cached: User prefers light mode"},
                {"id": "c2", "text": "Cached: User is a JavaScript developer"},
            ],
            "raw": [...],
            "summary": {"count": 2},
        },
    }

    demo_scenario(
        "Scenario 2: Using Cached State",
        state_2
    )

    # ========================================================================
    # Scenario 3: Force reload
    # ========================================================================
    fake_client_3 = FakeMem0Client(
        response_data={
            "success": True,
            "message": "ok",
            "data": [
                {"id": "new1", "text": "Updated: User switched to Rust"},
            ]
        }
    )

    state_3: GraphState = {
        "user_id": "user_123",
        "force_reload_mem0": True,  # Force reload even with cache
        "mem0_state": {
            "items": [{"id": "old", "text": "Old cached data"}],
            "raw": [...],
            "summary": {"count": 1},
        },
    }

    demo_scenario(
        "Scenario 3: Force Reload (Ignoring Cache)",
        state_3,
        client=fake_client_3
    )

    # ========================================================================
    # Scenario 4: API error handling
    # ========================================================================
    fake_client_4 = FakeMem0Client(
        response_data={
            "success": False,
            "message": "API rate limit exceeded",
            "data": None,
        }
    )

    state_4: GraphState = {
        "user_id": "user_456",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 4: API Error",
        state_4,
        client=fake_client_4
    )

    # ========================================================================
    # Scenario 5: Network exception
    # ========================================================================
    fake_client_5 = FakeMem0Client(
        should_raise=True,
        raise_error=Exception("Connection timeout after 30s")
    )

    state_5: GraphState = {
        "user_id": "user_789",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 5: Network Exception",
        state_5,
        client=fake_client_5
    )

    # ========================================================================
    # Scenario 6: Empty memories (valid state)
    # ========================================================================
    fake_client_6 = FakeMem0Client(
        response_data={
            "success": True,
            "message": "ok",
            "data": []  # No memories for new user
        }
    )

    state_6: GraphState = {
        "user_id": "new_user_001",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 6: Empty Memories (New User)",
        state_6,
        client=fake_client_6
    )

    # ========================================================================
    # Scenario 7: Dict with nested memories key
    # ========================================================================
    fake_client_7 = FakeMem0Client(
        response_data={
            "success": True,
            "message": "ok",
            "data": {
                "memories": [
                    {"id": "m1", "text": "Nested memory 1"},
                    {"id": "m2", "text": "Nested memory 2"},
                ],
                "pagination": {
                    "page": 1,
                    "total": 2
                }
            }
        }
    )

    state_7: GraphState = {
        "user_id": "user_999",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 7: Dict Response with Nested 'memories' Key",
        state_7,
        client=fake_client_7
    )

    # ========================================================================
    # Scenario 8: String items normalization
    # ========================================================================
    fake_client_8 = FakeMem0Client(
        response_data={
            "success": True,
            "message": "ok",
            "data": [
                "Simple string memory 1",
                "Simple string memory 2",
            ]
        }
    )

    state_8: GraphState = {
        "user_id": "user_string",
        "force_reload_mem0": False,
        "mem0_state": None,
    }

    demo_scenario(
        "Scenario 8: String Items (Auto-wrapped)",
        state_8,
        client=fake_client_8
    )

    print_separator("DEMO COMPLETE")
    print("\nKey Takeaways:")
    print("1. Router intelligently decides load vs. use based on cache state")
    print("2. Force reload bypasses cache for fresh data")
    print("3. Errors are gracefully handled and reported in mem0_error")
    print("4. Various response formats are normalized to consistent structure")
    print("5. Empty memories are valid (not treated as errors)")
    print_separator()


if __name__ == "__main__":
    main()
