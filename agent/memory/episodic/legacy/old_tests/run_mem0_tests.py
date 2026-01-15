"""
Test runner for mem0_nodes tests
"""

import sys
from test_mem0_nodes import *


def run_test(test_func, test_name):
    """Run a single test function and report result"""
    try:
        test_func()
        print(f"✓ {test_name}")
        return True
    except AssertionError as e:
        print(f"✗ {test_name}: {e}")
        return False
    except Exception as e:
        print(f"✗ {test_name}: Unexpected error: {e}")
        return False


def main():
    """Run all mem0 tests"""
    print("=" * 60)
    print("Running mem0_nodes tests")
    print("=" * 60)

    test_classes = [
        TestNormalizeMem0Items,
        TestSafeStr,
        TestMem0NeededRouter,
        TestLoadMem0,
        TestUseMem0State,
        TestMem0Integration,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()

        # Get all test methods
        test_methods = [m for m in dir(instance) if m.startswith('test_')]

        for method_name in test_methods:
            test_method = getattr(instance, method_name)
            total_tests += 1
            if run_test(test_method, f"  {method_name}"):
                passed_tests += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("=" * 60)

    if passed_tests == total_tests:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {total_tests - passed_tests} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
