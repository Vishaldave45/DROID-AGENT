#!/usr/bin/env python3
"""Automated Test Runner for NexForge Droid."""

import os
import sys
import unittest

# Ensure the nexforge-droid root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def run_all_tests() -> bool:
    """Discovers and executes all test suites under tests/."""
    print("=" * 60)
    print("      NEXFORGE DROID - AUTOMATED TEST SUITE EXECUTION")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(BASE_DIR, "tests"),
        pattern="test_*.py",
        top_level_dir=BASE_DIR,
    )

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 60)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Failures        : {len(result.failures)}")
    print(f"Errors          : {len(result.errors)}")
    print(f"Success         : {result.wasSuccessful()}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
