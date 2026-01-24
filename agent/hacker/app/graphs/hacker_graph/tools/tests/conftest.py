"""
Pytest configuration and shared fixtures for tool tests.
"""

import os
import sys
import pytest

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session")
def fixtures_dir():
    """Path to test fixtures directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="session")
def project_root():
    """Path to project root."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def external_sources_dir():
    """Path to external_sources directory."""
    return os.path.join(PROJECT_ROOT, "app", "external_sources")
