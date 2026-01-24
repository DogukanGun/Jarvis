"""
Tests for sql_injection_sqlmap tool.

Prerequisites:
    1. Start the vulnerable app:
       python vulnerable_app.py

    2. Start sqlmap API server:
       cd external_sources/sqlmap && python sqlmapapi.py -s -H 127.0.0.1 -p 8775

Usage:
    pytest test_sql_injection_sqlmap.py -v
    pytest test_sql_injection_sqlmap.py -v -k "test_client"  # Run specific tests
"""

import os
import sys
import time
import pytest
import requests
import subprocess
from typing import Generator

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.graphs.hacker_graph.tools.sql_injection_sqlmap import (
    SQLMapClient,
    sql_injection_sqlmap,
)


# Test configuration
VULNERABLE_APP_URL = "http://127.0.0.1:8666"
SQLMAP_API_URL = "http://127.0.0.1:8775"


# --- Fixtures ---

@pytest.fixture(scope="module")
def vulnerable_app() -> Generator[str, None, None]:
    """Start vulnerable FastAPI app for testing."""
    app_path = os.path.join(os.path.dirname(__file__), "vulnerable_app.py")

    # Check if already running
    try:
        resp = requests.get(f"{VULNERABLE_APP_URL}/health", timeout=2)
        if resp.status_code == 200:
            yield VULNERABLE_APP_URL
            return
    except requests.exceptions.ConnectionError:
        pass

    # Start the app
    proc = subprocess.Popen(
        [sys.executable, app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for startup
    max_wait = 10
    for _ in range(max_wait):
        try:
            resp = requests.get(f"{VULNERABLE_APP_URL}/health", timeout=1)
            if resp.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("Vulnerable app failed to start")

    yield VULNERABLE_APP_URL

    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def sqlmap_client() -> SQLMapClient:
    """Create SQLMapClient instance."""
    return SQLMapClient()


@pytest.fixture(scope="module")
def sqlmap_server_running() -> bool:
    """Check if sqlmap API server is running."""
    try:
        resp = requests.get(f"{SQLMAP_API_URL}/version", timeout=2)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# --- SQLMapClient Tests ---

class TestSQLMapClient:
    """Tests for SQLMapClient class."""

    def test_client_init(self, sqlmap_client: SQLMapClient):
        """Test client initialization."""
        assert sqlmap_client is not None
        assert sqlmap_client.base_url == SQLMAP_API_URL

    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_is_server_running(self, sqlmap_client: SQLMapClient):
        """Test server availability check."""
        # This will only run if server is available
        assert sqlmap_client.is_server_running() is True

    def test_is_server_not_running(self):
        """Test server check when server is down."""
        client = SQLMapClient(port=9999)  # Wrong port
        assert client.is_server_running() is False

    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_get_version(self, sqlmap_client: SQLMapClient):
        """Test getting sqlmap version."""
        version = sqlmap_client.get_version()
        assert version is not None
        assert len(version) > 0

    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_create_and_delete_task(self, sqlmap_client: SQLMapClient):
        """Test task creation and deletion."""
        taskid = sqlmap_client.create_task()
        assert taskid is not None
        assert len(taskid) > 0

        # Clean up
        deleted = sqlmap_client.delete_task(taskid)
        assert deleted is True

    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_set_and_get_options(self, sqlmap_client: SQLMapClient):
        """Test setting and getting task options."""
        taskid = sqlmap_client.create_task()

        try:
            # Set options
            success = sqlmap_client.set_options(taskid, {
                "level": 2,
                "risk": 1,
                "batch": True
            })
            assert success is True

            # Get options
            options = sqlmap_client.get_options(taskid)
            assert options is not None
        finally:
            sqlmap_client.delete_task(taskid)


# --- Integration Tests with Vulnerable App ---

class TestSQLMapIntegration:
    """Integration tests with vulnerable application."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_scan_vulnerable_endpoint(self, vulnerable_app: str, sqlmap_client: SQLMapClient):
        """Test scanning a vulnerable endpoint."""
        target_url = f"{vulnerable_app}/users?id=1"

        taskid = sqlmap_client.create_task()
        try:
            # Start scan
            success = sqlmap_client.start_scan(
                taskid,
                target_url,
                level=1,
                risk=1,
                batch=True
            )
            assert success is True

            # Check status
            status = sqlmap_client.get_status(taskid)
            assert status is not None
            assert "status" in status

        finally:
            sqlmap_client.kill_scan(taskid)
            sqlmap_client.delete_task(taskid)


# --- Tool Function Tests ---

class TestSQLInjectionTool:
    """Tests for sql_injection_sqlmap LangChain tool."""

    def test_tool_has_required_attributes(self):
        """Test tool has required LangChain attributes."""
        assert hasattr(sql_injection_sqlmap, "name")
        assert hasattr(sql_injection_sqlmap, "description")
        assert hasattr(sql_injection_sqlmap, "invoke")
        assert sql_injection_sqlmap.name == "sql_injection_sqlmap"

    def test_tool_with_invalid_url(self):
        """Test tool with invalid URL format."""
        from pydantic import ValidationError

        # Pydantic validation should reject invalid URL before tool runs
        with pytest.raises(ValidationError) as exc_info:
            sql_injection_sqlmap.invoke({
                "url": "not-a-valid-url",
                "level": 1,
                "risk": 1
            })
        assert "url" in str(exc_info.value).lower()

    def test_tool_with_missing_server(self):
        """Test tool when sqlmap server is not running."""
        # Use a URL that won't have a server
        result = sql_injection_sqlmap.invoke({
            "url": "http://localhost:9999/test?id=1",
            "level": 1,
            "risk": 1
        })
        # Should handle gracefully
        assert isinstance(result, str)

    @pytest.mark.slow
    @pytest.mark.skipif(
        not requests.get(f"{SQLMAP_API_URL}/version", timeout=2).ok if requests.get(f"{SQLMAP_API_URL}/version", timeout=2) else True,
        reason="SQLMap API server not running"
    )
    def test_tool_scan_vulnerable_endpoint(self, vulnerable_app: str):
        """Test tool against vulnerable endpoint."""
        result = sql_injection_sqlmap.invoke({
            "url": f"{vulnerable_app}/users?id=1",
            "level": 1,
            "risk": 1,
            "technique": "B"  # Boolean-based only for speed
        })

        assert isinstance(result, str)
        # Should complete without error
        assert "Error:" not in result or "timed out" in result.lower()


# --- Input Validation Tests ---

class TestInputValidation:
    """Tests for input validation."""

    def test_valid_url_validation(self):
        """Test URL validation passes for valid URLs."""
        from app.graphs.hacker_graph.tools.sql_injection_sqlmap import SQLMapScanInput

        # Should not raise
        input_data = SQLMapScanInput(
            url="http://example.com/page?id=1",
            level=1,
            risk=1
        )
        assert input_data.url == "http://example.com/page?id=1"

    def test_invalid_url_validation(self):
        """Test URL validation fails for invalid URLs."""
        from app.graphs.hacker_graph.tools.sql_injection_sqlmap import SQLMapScanInput

        with pytest.raises(ValueError):
            SQLMapScanInput(
                url="not-a-url",
                level=1,
                risk=1
            )

    def test_level_validation(self):
        """Test level parameter validation."""
        from app.graphs.hacker_graph.tools.sql_injection_sqlmap import SQLMapScanInput

        # Valid levels
        for level in [1, 2, 3, 4, 5]:
            input_data = SQLMapScanInput(url="http://test.com?id=1", level=level)
            assert input_data.level == level

        # Invalid levels
        with pytest.raises(ValueError):
            SQLMapScanInput(url="http://test.com?id=1", level=0)

        with pytest.raises(ValueError):
            SQLMapScanInput(url="http://test.com?id=1", level=6)

    def test_risk_validation(self):
        """Test risk parameter validation."""
        from app.graphs.hacker_graph.tools.sql_injection_sqlmap import SQLMapScanInput

        # Valid risks
        for risk in [1, 2, 3]:
            input_data = SQLMapScanInput(url="http://test.com?id=1", risk=risk)
            assert input_data.risk == risk

        # Invalid risks
        with pytest.raises(ValueError):
            SQLMapScanInput(url="http://test.com?id=1", risk=0)

        with pytest.raises(ValueError):
            SQLMapScanInput(url="http://test.com?id=1", risk=4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
