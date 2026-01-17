import json
import time
import subprocess
import os
from typing import Optional, Dict, Any, List

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator


SQLMAP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "external_sources", "sqlmap"
)


class SQLMapClient:
    """
    REST API client for sqlmap.

    Usage:
        # First start the server: python sqlmapapi.py -s -H 127.0.0.1 -p 8775
        client = SQLMapClient()
        result = client.scan("http://target.com/page?id=1", level=1, risk=1)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8775, timeout: int = 10):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, endpoint: str) -> Dict[str, Any]:
        resp = self.session.get(f"{self.base_url}{endpoint}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(
            f"{self.base_url}{endpoint}",
            json=data,
            timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def is_server_running(self) -> bool:
        """Check if sqlmap API server is running."""
        try:
            self._get("/version")
            return True
        except Exception:
            return False

    def get_version(self) -> str:
        """Get sqlmap version."""
        return self._get("/version").get("version", "unknown")

    def create_task(self) -> str:
        """Create a new scan task. Returns task ID."""
        result = self._get("/task/new")
        if not result.get("success"):
            raise RuntimeError("Failed to create task")
        return result["taskid"]

    def delete_task(self, taskid: str) -> bool:
        """Delete a task."""
        result = self._get(f"/task/{taskid}/delete")
        return result.get("success", False)

    def set_options(self, taskid: str, options: Dict[str, Any]) -> bool:
        """Set options for a task."""
        result = self._post(f"/option/{taskid}/set", options)
        return result.get("success", False)

    def get_options(self, taskid: str) -> Dict[str, Any]:
        """Get current options for a task."""
        return self._get(f"/option/{taskid}/list")

    def start_scan(self, taskid: str, url: str, **options) -> bool:
        """Start a scan with the given URL and options."""
        scan_options = {"url": url, **options}
        result = self._post(f"/scan/{taskid}/start", scan_options)
        return result.get("success", False)

    def get_status(self, taskid: str) -> Dict[str, Any]:
        """Get scan status. Returns dict with 'status' and 'returncode'."""
        return self._get(f"/scan/{taskid}/status")

    def get_data(self, taskid: str) -> Dict[str, Any]:
        """Get scan results/data."""
        return self._get(f"/scan/{taskid}/data")

    def get_log(self, taskid: str) -> List[Dict[str, Any]]:
        """Get scan logs."""
        result = self._get(f"/scan/{taskid}/log")
        return result.get("log", [])

    def stop_scan(self, taskid: str) -> bool:
        """Stop a running scan."""
        result = self._get(f"/scan/{taskid}/stop")
        return result.get("success", False)

    def kill_scan(self, taskid: str) -> bool:
        """Force kill a scan."""
        result = self._get(f"/scan/{taskid}/kill")
        return result.get("success", False)

    def wait_for_completion(
        self,
        taskid: str,
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Wait for scan to complete and return results.

        Args:
            taskid: Task ID to wait for
            timeout: Max wait time in seconds
            poll_interval: How often to check status

        Returns:
            Scan data/results
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status(taskid)
            if status.get("status") == "terminated":
                return self.get_data(taskid)
            time.sleep(poll_interval)
        raise TimeoutError(f"Scan did not complete within {timeout}s")

    def scan(
        self,
        url: str,
        level: int = 1,
        risk: int = 1,
        timeout: int = 300,
        **extra_options
    ) -> Dict[str, Any]:
        """
        Convenience method: create task, start scan, wait for results, cleanup.

        Args:
            url: Target URL with injectable parameter
            level: Test level (1-5)
            risk: Risk level (1-3)
            timeout: Max scan time in seconds
            **extra_options: Additional sqlmap options

        Returns:
            Scan results dict
        """
        taskid = self.create_task()
        try:
            options = {
                "level": level,
                "risk": risk,
                "batch": True,  # Non-interactive
                "randomAgent": True,
                **extra_options
            }

            if not self.start_scan(taskid, url, **options):
                raise RuntimeError("Failed to start scan")

            return self.wait_for_completion(taskid, timeout=timeout)
        finally:
            self.delete_task(taskid)


class SQLMapScanInput(BaseModel):
    url: str = Field(
        ...,
        description="Target URL with parameter to test (e.g., 'http://example.com/page?id=1')"
    )
    level: int = Field(
        1,
        description="Level of tests to perform (1-5). Higher = more tests but slower."
    )
    risk: int = Field(
        1,
        description="Risk of tests (1-3). Higher = more intrusive tests."
    )
    data: Optional[str] = Field(
        None,
        description="POST data string (e.g., 'username=test&password=test')"
    )
    cookie: Optional[str] = Field(
        None,
        description="HTTP Cookie header value"
    )
    technique: str = Field(
        "BEUSTQ",
        description="SQL injection techniques to test: B=Boolean, E=Error, U=Union, S=Stacked, T=Time, Q=Inline"
    )
    dbs: bool = Field(
        False,
        description="Enumerate DBMS databases"
    )
    tables: bool = Field(
        False,
        description="Enumerate DBMS database tables"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("level must be between 1 and 5")
        return v

    @field_validator("risk")
    @classmethod
    def validate_risk(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("risk must be between 1 and 3")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        if any(ch in v for ch in [";", "|", "`", "$"]):
            raise ValueError("Invalid characters in URL")
        return v


def _start_sqlmap_server(host: str = "127.0.0.1", port: int = 8775) -> subprocess.Popen:
    """Start sqlmap API server as background process."""
    sqlmapapi_path = os.path.join(SQLMAP_PATH, "sqlmapapi.py")
    proc = subprocess.Popen(
        ["python", sqlmapapi_path, "-s", "-H", host, "-p", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=SQLMAP_PATH
    )
    # Give server time to start
    time.sleep(2)
    return proc


def _format_scan_results(data: Dict[str, Any], logs: List[Dict[str, Any]]) -> str:
    """Format scan results for readable output."""
    lines = []

    # Extract findings from data
    scan_data = data.get("data", [])
    if scan_data:
        lines.append("=== SCAN FINDINGS ===")
        for item in scan_data:
            status = item.get("status")
            value = item.get("value")
            if value:
                if isinstance(value, dict):
                    lines.append(json.dumps(value, indent=2))
                else:
                    lines.append(str(value))

    # Extract key log messages
    important_logs = []
    for log in logs:
        msg = log.get("message", "")
        level = log.get("level", "")
        if any(kw in msg.lower() for kw in [
            "injectable", "parameter", "payload", "dbms",
            "vulnerable", "injection", "database", "table"
        ]):
            important_logs.append(f"[{level}] {msg}")

    if important_logs:
        lines.append("\n=== KEY LOG MESSAGES ===")
        lines.extend(important_logs[-20:])  # Last 20 relevant messages

    if not lines:
        lines.append("No SQL injection vulnerabilities found.")

    output = "\n".join(lines)
    if len(output) > 8000:
        output = output[:8000] + "\n...[truncated]..."
    return output


@tool("sql_injection_sqlmap", args_schema=SQLMapScanInput)
def sql_injection_sqlmap(
    url: str,
    level: int = 1,
    risk: int = 1,
    data: Optional[str] = None,
    cookie: Optional[str] = None,
    technique: str = "BEUSTQ",
    dbs: bool = False,
    tables: bool = False
) -> str:
    """
    Scan a URL for SQL injection vulnerabilities using sqlmap.

    This tool uses sqlmap's REST API to perform SQL injection testing.
    The API server must be running (started automatically if not).

    Returns detected vulnerabilities, injectable parameters, and database info.
    """
    client = SQLMapClient()
    server_proc = None

    try:
        # Start server if not running
        if not client.is_server_running():
            server_proc = _start_sqlmap_server()
            if not client.is_server_running():
                return "Error: Failed to start sqlmap API server"

        # Build options
        options = {
            "technique": technique,
            "batch": True,
            "randomAgent": True,
        }
        if data:
            options["data"] = data
        if cookie:
            options["cookie"] = cookie
        if dbs:
            options["getDbs"] = True
        if tables:
            options["getTables"] = True

        # Run scan
        taskid = client.create_task()
        try:
            if not client.start_scan(taskid, url, level=level, risk=risk, **options):
                return "Error: Failed to start scan"

            # Wait for completion (max 5 minutes)
            result = client.wait_for_completion(taskid, timeout=300, poll_interval=3)
            logs = client.get_log(taskid)

            return _format_scan_results(result, logs)

        finally:
            client.delete_task(taskid)

    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to sqlmap API server. Start it with: python sqlmapapi.py -s"
    except TimeoutError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        if server_proc:
            server_proc.terminate()
