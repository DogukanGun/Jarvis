"""
Demo script for preprocess_input node

Shows how the node works with various example prompts
"""

from preprocess_node import preprocess_input, TaskType, GraphState
import json


def demo_prompt(prompt: str, context: dict = None):
    """Run preprocessing on a prompt and display results"""
    print("\n" + "=" * 70)
    print(f"PROMPT: {prompt}")
    if context:
        print(f"CONTEXT: {context}")
    print("-" * 70)

    state: GraphState = {
        "prompt": prompt,
        "context": context,
    }

    result = preprocess_input(state)

    print(f"Task Type:    {result['task_type']}")
    print(f"App:          {result['app']}")
    print(f"Entities:     {result['entities']}")
    print(f"Normalized:   {result['normalized_prompt']}")
    print(f"Keywords:     {result['preprocess_meta']['matched_keywords']}")


def main():
    """Run demo examples"""
    print("\n" + "=" * 70)
    print("JARVIS PREPROCESS NODE DEMO")
    print("Node 1: preprocess_input - MainGraph")
    print("=" * 70)

    # Example 1: Send email
    demo_prompt("send email to john.doe@example.com about the meeting")

    # Example 2: Login with 2FA (priority over email)
    demo_prompt("login to gmail with 2fa code to send email")

    # Example 3: Fill form on LinkedIn
    demo_prompt("fill out the linkedin job application form")

    # Example 4: Search and browse
    demo_prompt("search for the latest AI research papers")

    # Example 5: Upload files
    demo_prompt("upload the pdf document to the server")

    # Example 6: Complex prompt with multiple entities
    demo_prompt(
        "login to gmail and send email to John Smith at john@example.com "
        "with the document from https://example.com/report.pdf"
    )

    # Example 7: Using context
    demo_prompt(
        "send email to the team",
        context={"current_app": "outlook"}
    )

    # Example 8: Chat (short conversational)
    demo_prompt("hello there")

    # Example 9: Unknown (long without keywords)
    demo_prompt(
        "this is a very complex instruction that doesn't really fit "
        "into any specific category we have defined"
    )

    # Example 10: Form with names
    demo_prompt(
        "fill the registration form for Jane Doe and Bob Smith "
        "at contact@company.com"
    )

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
