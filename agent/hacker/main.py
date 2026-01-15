#!/usr/bin/env python3
"""
Jarvis Hacker Agent - Entry Point

Two-phase AI agent system:
1. Planner Agent - Context-aware, decides what CLI actions to take
2. Compiler Agent - Context-blind, converts decisions to structured tool calls
"""
import logging
import sys

from app.graphs.hacker_graph import run_hacker_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Hacker Agent."""
    # Get user input from command line or interactive
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        print("Jarvis Hacker Agent")
        print("=" * 40)
        user_input = input("Enter your request: ").strip()

    if not user_input:
        print("No input provided. Exiting.")
        return

    print(f"\nProcessing: {user_input}")
    print("-" * 40)

    try:
        # Run the agent
        result = run_hacker_graph(user_input)

        # Print results
        print("\n" + "=" * 40)
        print("RESULT")
        print("=" * 40)

        final_answer = result.get("final_answer")
        if final_answer:
            print(f"\nAnswer: {final_answer}")
        else:
            print("\nNo final answer generated.")

        # Print execution summary
        tool_history = result.get("tool_history", [])
        if tool_history:
            print(f"\nCommands executed: {len(tool_history)}")
            for i, tool_result in enumerate(tool_history, 1):
                cmd = tool_result.get("cmd", "unknown")
                exit_code = tool_result.get("exit_code", -1)
                status = "OK" if exit_code == 0 else "FAILED"
                print(f"  {i}. [{status}] {cmd}")

        # Print any errors
        errors = result.get("errors", [])
        if errors:
            print(f"\nErrors encountered: {len(errors)}")
            for error in errors:
                print(f"  - {error}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        logger.exception("Hacker Agent failed")
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
