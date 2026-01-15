"""
Combined test runner for all episodic memory nodes

Runs all tests for Node 1 (preprocess) and Nodes 2-4 (mem0)
"""

import sys
import subprocess


def run_test_file(test_runner, name):
    """Run a test file and return success status"""
    print(f"\n{'=' * 70}")
    print(f"Running {name}")
    print('=' * 70)

    try:
        result = subprocess.run(
            ["python", test_runner],
            capture_output=True,
            text=True
        )

        # Print output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"Error running {test_runner}: {e}", file=sys.stderr)
        return False


def main():
    """Run all test suites"""
    print("=" * 70)
    print("JARVIS EPISODIC MEMORY - COMPLETE TEST SUITE")
    print("=" * 70)

    results = {}

    # Run Node 1 tests (preprocess)
    results["Node 1 (Preprocess)"] = run_test_file(
        "run_tests.py",
        "Node 1: preprocess_input Tests"
    )

    # Run Nodes 2-4 tests (mem0)
    results["Nodes 2-4 (Mem0)"] = run_test_file(
        "run_mem0_tests.py",
        "Nodes 2-4: Mem0 Handling Tests"
    )

    # Run Node 5 tests (episodes)
    results["Node 5 (Episodes)"] = run_test_file(
        "run_episodes_tests.py",
        "Node 5: retrieve_episodes Tests"
    )

    # Summary
    print("\n" + "=" * 70)
    print("OVERALL TEST SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for success in results.values() if success)

    for suite, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{suite:30s} {status}")

    print("=" * 70)
    print(f"Test Suites: {passed}/{total} passed")

    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print(f"❌ {total - passed} test suite(s) failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
