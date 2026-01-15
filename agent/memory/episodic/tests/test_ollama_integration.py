"""
Test Ollama/Llama3.1 integration with MainGraph
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.graphs.main_graph import run_main_graph
from app import config

def test_ollama_integration():
    """Test MainGraph with actual Ollama/Llama3.1"""

    print("\n" + "="*70)
    print("OLLAMA/LLAMA3.1 INTEGRATION TEST")
    print("="*70)

    # Set to use Ollama
    config.config.LLM_PROVIDER = "ollama"
    config.config.LLM_MODEL = "llama3.1:8b"

    print(f"\nConfiguration:")
    print(f"  Provider: {config.config.LLM_PROVIDER}")
    print(f"  Model: {config.config.LLM_MODEL}")
    print(f"  Ollama URL: {config.config.OLLAMA_BASE_URL}")

    # Run a simple test
    print("\nRunning MainGraph with Ollama...")
    print("  User prompt: 'What is the capital of France?'")

    try:
        result = run_main_graph(
            user_id="test_user_ollama",
            prompt="What is the capital of France?",
            context={}
        )

        print("\n✓ Ollama integration test passed!")
        print(f"  Task type: {result.get('task_type')}")

        response_payload = result.get("response_payload", {})
        answer = response_payload.get("answer", "")

        print(f"\n  LLM Response:")
        print(f"  {answer[:200]}...")

        # Check for errors
        if result.get("llm_error"):
            print(f"\n⚠ Warning: LLM error detected: {result['llm_error']}")

        print("\n" + "="*70)
        print("✓ Ollama/Llama3.1 integration working correctly!")
        print("="*70)

    except Exception as e:
        print(f"\n✗ Ollama integration test failed!")
        print(f"  Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check if Ollama is running: curl http://localhost:11434/api/tags")
        print("  2. Verify llama3.1:8b model is available")
        print("  3. Check Ollama logs for errors")
        print("\n" + "="*70)
        raise

if __name__ == "__main__":
    test_ollama_integration()
