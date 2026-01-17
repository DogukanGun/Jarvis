import sys
import os
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

# Add ChSSHKracker to path
CHSSHKRACKER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "external_sources", "ChSSHKracker"
)
sys.path.insert(0, CHSSHKRACKER_PATH)

# Lazy imports - ChSSHKracker requires paramiko
_ChSSHKracker = None
_AttackConfig = None
_AttackResult = None
_ServerInfo = None
_IMPORT_ERROR = None


def _lazy_import():
    """Lazily import ChSSHKracker dependencies."""
    global _ChSSHKracker, _AttackConfig, _AttackResult, _ServerInfo, _IMPORT_ERROR

    if _ChSSHKracker is not None or _IMPORT_ERROR is not None:
        return

    try:
        from ChSshKracker import ChSSHKracker, AttackConfig, AttackResult
        from core.models import ServerInfo
        _ChSSHKracker = ChSSHKracker
        _AttackConfig = AttackConfig
        _AttackResult = AttackResult
        _ServerInfo = ServerInfo
    except ImportError as e:
        _IMPORT_ERROR = str(e)


def _check_dependencies() -> Optional[str]:
    """Check if dependencies are available. Returns error message if not."""
    _lazy_import()
    if _IMPORT_ERROR:
        return (
            f"ChSSHKracker dependencies not installed: {_IMPORT_ERROR}\n"
            "Install with: pip install paramiko cryptography colorama"
        )
    return None


class SSHBruteForceInput(BaseModel):
    targets: str = Field(
        ...,
        description="Comma-separated list of targets as ip:port (e.g., '192.168.1.1:22,192.168.1.2:22')"
    )
    usernames: str = Field(
        ...,
        description="Comma-separated list of usernames to try (e.g., 'root,admin,ubuntu')"
    )
    passwords: str = Field(
        ...,
        description="Comma-separated list of passwords to try (e.g., 'password,admin,123456')"
    )
    timeout: int = Field(
        5,
        description="SSH connection timeout in seconds"
    )
    max_workers: int = Field(
        10,
        description="Maximum concurrent worker threads"
    )
    per_worker: int = Field(
        5,
        description="Concurrent tasks per worker thread"
    )

    @field_validator("targets")
    @classmethod
    def validate_targets(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("targets cannot be empty")
        # Basic validation
        for target in v.split(","):
            target = target.strip()
            if target and ":" not in target:
                raise ValueError(f"Invalid target format '{target}'. Use ip:port format.")
        return v

    @field_validator("usernames")
    @classmethod
    def validate_usernames(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("usernames cannot be empty")
        return v

    @field_validator("passwords")
    @classmethod
    def validate_passwords(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("passwords cannot be empty")
        return v

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_workers must be between 1 and 50")
        return v

    @field_validator("per_worker")
    @classmethod
    def validate_per_worker(cls, v: int) -> int:
        if v < 1 or v > 25:
            raise ValueError("per_worker must be between 1 and 25")
        return v


class SSHBruteForceClient:
    """
    Client wrapper for ChSSHKracker SSH brute force tool.

    Usage:
        client = SSHBruteForceClient()

        # Run attack with direct lists
        result = client.attack(
            targets=[("192.168.1.1", "22")],
            combos=[("root", "password"), ("admin", "admin123")],
            timeout=5
        )

        # Check results
        for server in result.success_list:
            print(f"Valid: {server.ip}:{server.port} - {server.username}:{server.password}")
    """

    def __init__(self):
        err = _check_dependencies()
        if err:
            raise ImportError(err)
        _lazy_import()
        self.kracker = _ChSSHKracker()

    def attack(
        self,
        targets: List[tuple],
        combos: List[tuple],
        timeout: int = 5,
        max_workers: int = 10,
        per_worker: int = 5,
        on_success: Optional[callable] = None,
        on_honeypot: Optional[callable] = None,
        on_progress: Optional[callable] = None
    ):
        """
        Run SSH brute force attack.

        Args:
            targets: List of (ip, port) tuples
            combos: List of (username, password) tuples
            timeout: SSH connection timeout
            max_workers: Max concurrent worker threads
            per_worker: Tasks per worker
            on_success: Callback for valid credentials
            on_honeypot: Callback for honeypot detection
            on_progress: Callback for progress updates

        Returns:
            AttackResult with statistics and findings
        """
        config = _AttackConfig(
            targets=targets,
            combos=combos,
            timeout=timeout,
            max_workers=max_workers,
            per_worker=per_worker
        )

        return self.kracker.run(
            config,
            on_success=on_success,
            on_honeypot=on_honeypot,
            on_progress=on_progress
        )

    def attack_from_files(
        self,
        ip_file: str,
        combo_file: Optional[str] = None,
        username_file: Optional[str] = None,
        password_file: Optional[str] = None,
        timeout: int = 5,
        max_workers: int = 10,
        per_worker: int = 5
    ):
        """
        Run SSH brute force attack using credential files.

        Args:
            ip_file: File with IP:port per line
            combo_file: File with username:password per line
            username_file: File with usernames (one per line)
            password_file: File with passwords (one per line)
            timeout: SSH connection timeout
            max_workers: Max concurrent workers
            per_worker: Tasks per worker

        Returns:
            AttackResult with statistics and findings
        """
        config = _AttackConfig(
            ip_file=ip_file,
            combo_file=combo_file,
            username_file=username_file,
            password_file=password_file,
            timeout=timeout,
            max_workers=max_workers,
            per_worker=per_worker
        )

        return self.kracker.run(config)

    def stop(self) -> None:
        """Stop any running attack."""
        self.kracker.stop()


def _parse_targets(targets_str: str) -> List[tuple]:
    """Parse comma-separated targets into list of tuples."""
    targets = []
    for target in targets_str.split(","):
        target = target.strip()
        if target:
            parts = target.split(":")
            if len(parts) == 2:
                targets.append((parts[0], parts[1]))
            elif len(parts) == 1:
                targets.append((parts[0], "22"))  # Default port
    return targets


def _parse_combos(usernames_str: str, passwords_str: str) -> List[tuple]:
    """Generate username:password combinations."""
    usernames = [u.strip() for u in usernames_str.split(",") if u.strip()]
    passwords = [p.strip() for p in passwords_str.split(",") if p.strip()]

    combos = []
    for username in usernames:
        for password in passwords:
            combos.append((username, password))
    return combos


def _format_server_info(server) -> Dict[str, Any]:
    """Convert ServerInfo to dict."""
    return {
        "ip": server.ip,
        "port": server.port,
        "username": server.username,
        "password": server.password,
        "is_honeypot": server.is_honeypot,
        "honeypot_score": server.honeypot_score,
        "ssh_version": server.ssh_version,
        "os_info": server.os_info,
        "hostname": server.hostname,
        "response_time_ms": server.response_time_ms
    }


def _format_result(result) -> str:
    """Format attack result for output."""
    lines = []

    # Summary
    lines.append("=== SSH BRUTE FORCE RESULTS ===")
    lines.append(f"Total combinations tested: {result.total_tasks}")
    lines.append(f"Valid credentials found: {result.goods}")
    lines.append(f"Honeypots detected: {result.honeypots}")
    lines.append(f"Errors: {result.errors}")
    lines.append("")

    # Valid credentials
    if result.success_list:
        lines.append("=== VALID CREDENTIALS ===")
        for server in result.success_list:
            lines.append(f"  {server.ip}:{server.port}")
            lines.append(f"    Username: {server.username}")
            lines.append(f"    Password: {server.password}")
            if server.os_info:
                lines.append(f"    OS: {server.os_info[:50]}")
            if server.ssh_version:
                lines.append(f"    SSH: {server.ssh_version}")
            if server.hostname:
                lines.append(f"    Hostname: {server.hostname}")
            lines.append("")

    # Honeypots
    if result.honeypot_list:
        lines.append("=== DETECTED HONEYPOTS ===")
        for server in result.honeypot_list:
            lines.append(f"  {server.ip}:{server.port} (score: {server.honeypot_score})")

    if not result.success_list and not result.honeypot_list:
        lines.append("No valid credentials found.")

    output = "\n".join(lines)
    if len(output) > 8000:
        output = output[:8000] + "\n...[truncated]..."
    return output


@tool("ssh_brute_force", args_schema=SSHBruteForceInput)
def ssh_brute_force(
    targets: str,
    usernames: str,
    passwords: str,
    timeout: int = 5,
    max_workers: int = 10,
    per_worker: int = 5
) -> str:
    """
    Test SSH credentials against target hosts using brute force.

    This tool attempts to authenticate to SSH servers using provided
    username/password combinations. It includes:
    - Multi-threaded connection handling
    - Honeypot detection
    - System reconnaissance on successful auth

    Use responsibly and only on systems you have permission to test.

    Args:
        targets: Comma-separated IP:port pairs (e.g., '192.168.1.1:22,10.0.0.5:22')
        usernames: Comma-separated usernames (e.g., 'root,admin,ubuntu')
        passwords: Comma-separated passwords (e.g., 'password,admin123,root')
        timeout: Connection timeout in seconds
        max_workers: Concurrent worker threads (1-50)
        per_worker: Tasks per worker (1-25)

    Returns:
        Report of valid credentials, honeypots detected, and statistics
    """
    # Check dependencies
    err = _check_dependencies()
    if err:
        return f"Error: {err}"

    try:
        # Parse inputs
        target_list = _parse_targets(targets)
        combo_list = _parse_combos(usernames, passwords)

        if not target_list:
            return "Error: No valid targets provided"
        if not combo_list:
            return "Error: No valid username/password combinations"

        # Limit combinations to prevent excessive runtime
        max_combos = 1000
        if len(target_list) * len(combo_list) > max_combos:
            return (
                f"Error: Too many combinations ({len(target_list)} targets × "
                f"{len(combo_list)} combos = {len(target_list) * len(combo_list)}). "
                f"Maximum allowed: {max_combos}"
            )

        # Run attack
        client = SSHBruteForceClient()
        result = client.attack(
            targets=target_list,
            combos=combo_list,
            timeout=timeout,
            max_workers=max_workers,
            per_worker=per_worker
        )

        return _format_result(result)

    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@tool("ssh_credential_test")
def ssh_credential_test(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: int = 5
) -> str:
    """
    Test a single SSH credential against a host.

    Simpler alternative to ssh_brute_force for testing one credential pair.

    Args:
        host: Target IP or hostname
        port: SSH port (usually 22)
        username: Username to test
        password: Password to test
        timeout: Connection timeout in seconds

    Returns:
        Success/failure message with server details if successful
    """
    # Check dependencies
    err = _check_dependencies()
    if err:
        return f"Error: {err}"

    try:
        client = SSHBruteForceClient()
        result = client.attack(
            targets=[(host, str(port))],
            combos=[(username, password)],
            timeout=timeout,
            max_workers=1,
            per_worker=1
        )

        if result.success_list:
            server = result.success_list[0]
            lines = [
                "=== AUTHENTICATION SUCCESSFUL ===",
                f"Host: {server.ip}:{server.port}",
                f"Username: {server.username}",
                f"Password: {server.password}",
            ]
            if server.os_info:
                lines.append(f"OS: {server.os_info}")
            if server.ssh_version:
                lines.append(f"SSH Version: {server.ssh_version}")
            if server.hostname:
                lines.append(f"Hostname: {server.hostname}")
            if server.is_honeypot:
                lines.append(f"WARNING: Possible honeypot (score: {server.honeypot_score})")
            return "\n".join(lines)

        if result.honeypot_list:
            server = result.honeypot_list[0]
            return f"Honeypot detected at {host}:{port} (score: {server.honeypot_score})"

        return f"Authentication failed for {username}@{host}:{port}"

    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
