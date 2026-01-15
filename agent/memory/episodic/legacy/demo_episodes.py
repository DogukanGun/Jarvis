"""
Demo script for retrieve_episodes node

Shows how episode retrieval works with various scenarios.
"""

from episode_schema import create_episode, EpisodeType
from episode_storage import InMemoryEpisodeStorage, set_episode_storage
from retrieve_episodes_node import (
    retrieve_episodes,
    extract_episode_context,
    filter_episodes_by_relevance,
    GraphState,
)
from datetime import datetime, timedelta


def print_separator(title=""):
    """Print a visual separator"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)
    else:
        print()


def setup_demo_storage():
    """Create storage with realistic demo episodes"""
    storage = InMemoryEpisodeStorage()

    # Past week: Email tasks
    storage.insert(create_episode(
        user_id="demo_user",
        text="Sent project update email to team@company.com with Q4 report attachment",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="send_email",
        app="gmail",
        entities=["team@company.com", "gmail", "Q4 report"],
        importance_score=0.8,
        embedding=[0.5, 0.3, 0.8, 0.2, 0.6],  # "Email about project"
        response="Successfully sent email to team@company.com",
        timestamp=(datetime.utcnow() - timedelta(days=2)).isoformat()
    ))

    # Yesterday: LinkedIn form
    storage.insert(create_episode(
        user_id="demo_user",
        text="Filled job application form for Senior Engineer position at TechCorp",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="fill_form",
        app="linkedin",
        entities=["linkedin", "TechCorp", "Senior Engineer"],
        importance_score=0.9,
        embedding=[0.2, 0.7, 0.3, 0.9, 0.4],  # "Job application"
        response="Form submitted successfully",
        timestamp=(datetime.utcnow() - timedelta(days=1)).isoformat(),
        reinforcement_count=2,  # User came back to this
        verified=True
    ))

    # Today: Gmail login
    storage.insert(create_episode(
        user_id="demo_user",
        text="Logged into Gmail using 2FA code 123456",
        episode_type=EpisodeType.INTERACTION,
        task_type="login_auth",
        app="gmail",
        entities=["gmail", "2FA"],
        importance_score=0.4,
        embedding=[0.6, 0.2, 0.5, 0.1, 0.3],  # "Gmail login"
        response="Login successful",
        timestamp=datetime.utcnow().isoformat()
    ))

    # Last week: Search task
    storage.insert(create_episode(
        user_id="demo_user",
        text="Searched for Python asyncio best practices on Google",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="search_browse",
        entities=["Google", "Python", "asyncio"],
        importance_score=0.6,
        embedding=[0.3, 0.6, 0.2, 0.7, 0.5],  # "Python search"
        timestamp=(datetime.utcnow() - timedelta(days=7)).isoformat()
    ))

    # Old: Error episode
    storage.insert(create_episode(
        user_id="demo_user",
        text="Failed to send email: SMTP connection timeout",
        episode_type=EpisodeType.ERROR,
        task_type="send_email",
        app="gmail",
        entities=["gmail", "SMTP"],
        importance_score=0.7,
        embedding=[0.5, 0.3, 0.7, 0.3, 0.5],
        timestamp=(datetime.utcnow() - timedelta(days=30)).isoformat()
    ))

    # Different user episode (should not appear)
    storage.insert(create_episode(
        user_id="other_user",
        text="Other user's email to john@example.com",
        episode_type=EpisodeType.TASK_COMPLETION,
        task_type="send_email",
        app="outlook",
        entities=["john@example.com", "outlook"],
        importance_score=0.9
    ))

    return storage


def demo_scenario(title, state, storage):
    """Run a demo scenario"""
    print_separator(title)

    print("Query Context:")
    print(f"  User: {state.get('user_id')}")
    print(f"  Prompt: {state.get('normalized_prompt')}")
    print(f"  Task Type: {state.get('task_type', 'N/A')}")
    print(f"  App: {state.get('app', 'N/A')}")
    print(f"  Entities: {state.get('entities', [])}")

    # Retrieve episodes
    result = retrieve_episodes(state, storage=storage)

    print(f"\nRetrieval Results:")
    print(f"  Error: {result['episode_retrieval_error']}")
    print(f"  Episodes found: {result['episode_retrieval_meta']['episodes_found']}")
    print(f"  Episodes returned: {result['episode_retrieval_meta']['episodes_returned']}")
    print(f"  Query time: {result['episode_retrieval_meta']['query_time_ms']:.2f}ms")

    episodes = result["retrieved_episodes"]
    if episodes:
        print(f"\n  Top {len(episodes)} Episodes:")
        for i, ep_result in enumerate(episodes[:5], 1):
            episode = ep_result["episode"]
            score = ep_result["score"]
            reasons = ", ".join(ep_result["match_reasons"])

            print(f"\n  {i}. Score: {score:.3f}")
            print(f"     Text: {episode['text'][:70]}...")
            print(f"     Type: {episode['episode_type']} | Task: {episode.get('task_type', 'N/A')}")
            print(f"     App: {episode.get('app', 'N/A')} | Importance: {episode['importance_score']:.2f}")
            print(f"     Match: {reasons}")

        # Extract context
        context = extract_episode_context(episodes)
        print(f"\n  Extracted Context:")
        print(f"     Common task: {context['most_common_task_type']}")
        print(f"     Common app: {context['most_common_app']}")
        print(f"     Top entities: {context['top_entities'][:3]}")
        print(f"     Avg score: {context['avg_score']:.2f}")


def main():
    """Run demo scenarios"""
    print_separator("JARVIS EPISODE RETRIEVAL DEMO")
    print("Node 5: retrieve_episodes")
    print_separator()

    # Setup storage
    storage = setup_demo_storage()
    set_episode_storage(storage)

    print(f"\nDemo Storage Setup:")
    print(f"  Total episodes: {storage.count()}")
    print(f"  Users: demo_user, other_user")

    # ========================================================================
    # Scenario 1: General email query
    # ========================================================================
    state1: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "send email about project",
        "task_type": "send_email",
        "app": "gmail",
        "entities": [],
        "query_embedding": [0.5, 0.3, 0.8, 0.2, 0.6],  # Similar to email episode
    }

    demo_scenario(
        "Scenario 1: Email Query with Semantic Search",
        state1,
        storage
    )

    # ========================================================================
    # Scenario 2: LinkedIn form query
    # ========================================================================
    state2: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "fill linkedin application",
        "task_type": "fill_form",
        "app": "linkedin",
        "entities": ["linkedin"],
    }

    demo_scenario(
        "Scenario 2: LinkedIn Form Query with Filters",
        state2,
        storage
    )

    # ========================================================================
    # Scenario 3: Login query (recent boost)
    # ========================================================================
    state3: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "login to gmail",
        "task_type": "login_auth",
        "app": "gmail",
        "entities": ["gmail"],
    }

    demo_scenario(
        "Scenario 3: Login Query (Recent Episodes Boosted)",
        state3,
        storage
    )

    # ========================================================================
    # Scenario 4: Entity-based search
    # ========================================================================
    state4: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "email to team",
        "entities": ["team@company.com"],
    }

    demo_scenario(
        "Scenario 4: Entity-Based Search",
        state4,
        storage
    )

    # ========================================================================
    # Scenario 5: High importance filter
    # ========================================================================
    state5: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "important tasks",
        "context": {
            "episode_min_importance": 0.7,
            "episode_limit": 3,
        }
    }

    demo_scenario(
        "Scenario 5: High Importance Filter",
        state5,
        storage
    )

    # ========================================================================
    # Scenario 6: Recent episodes only
    # ========================================================================
    state6: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "recent activities",
        "context": {
            "episode_recent_days": 7,
        }
    }

    demo_scenario(
        "Scenario 6: Recent Episodes (Last 7 Days)",
        state6,
        storage
    )

    # ========================================================================
    # Scenario 7: No matches
    # ========================================================================
    state7: GraphState = {
        "user_id": "demo_user",
        "normalized_prompt": "check outlook calendar",
        "task_type": "fill_form",
        "app": "outlook",  # No outlook episodes for this user
    }

    demo_scenario(
        "Scenario 7: No Matching Episodes",
        state7,
        storage
    )

    print_separator("DEMO COMPLETE")
    print("\nKey Features Demonstrated:")
    print("1. Semantic search using embeddings")
    print("2. Multi-filter queries (task_type, app, entities)")
    print("3. Importance and confidence filtering")
    print("4. Recency and reinforcement boosting")
    print("5. User isolation (only sees own episodes)")
    print("6. Context extraction from results")
    print("7. Graceful handling of no matches")
    print_separator()


if __name__ == "__main__":
    main()
