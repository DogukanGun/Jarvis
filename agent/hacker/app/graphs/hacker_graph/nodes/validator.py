import logging
from typing import Dict, Any, Literal

from pydantic import ValidationError

from app.config import config
from app.graphs.hacker_graph.state import HackerGraphState
from app.schemas.tool_request import ToolRequest

logger = logging.getLogger(__name__)


def _check_allowlist(cmd: str) -> list[str]:
    """Check if command is in the allowlist."""
    errors = []

    if not config.COMMAND_ALLOWLIST:
        # Empty allowlist means all commands are allowed
        return errors

    # Get the base command (first word)
    base_cmd = cmd.strip().split()[0] if cmd.strip() else ""

    # Handle paths (e.g., /usr/bin/ls -> ls)
    if "/" in base_cmd:
        base_cmd = base_cmd.split("/")[-1]

    if base_cmd not in config.COMMAND_ALLOWLIST:
        errors.append(f"Command '{base_cmd}' is not in the allowlist. Allowed: {', '.join(config.COMMAND_ALLOWLIST)}")

    return errors


def _check_dangerous_patterns(cmd: str) -> list[str]:
    """Check for dangerous command patterns."""
    errors = []

    for pattern in config.DANGEROUS_PATTERNS:
        if pattern in cmd:
            errors.append(f"Dangerous pattern detected: '{pattern}'")

    return errors


def validator_node(state: HackerGraphState) -> Dict[str, Any]:
    """
    Validates ToolRequest JSON:
    - Schema validation (Pydantic)
    - Allowlist check (command whitelist)
    - Dangerous command detection

    Returns validation status and any errors.
    """
    logger.info("Validator node executing...")

    tool_request = state.get("tool_request")
    errors = []

    # Check if tool_request exists
    if not tool_request:
        errors.append("No tool request provided")
        return {
            "is_valid": False,
            "validation_errors": errors,
        }

    # Schema validation with Pydantic
    try:
        validated = ToolRequest(**tool_request)
        cmd = validated.args.cmd
    except ValidationError as e:
        for err in e.errors():
            errors.append(f"Schema error: {err['msg']} at {'.'.join(str(x) for x in err['loc'])}")
        return {
            "is_valid": False,
            "validation_errors": errors,
        }

    # Check allowlist
    allowlist_errors = _check_allowlist(cmd)
    errors.extend(allowlist_errors)

    # Check dangerous patterns
    dangerous_errors = _check_dangerous_patterns(cmd)
    errors.extend(dangerous_errors)

    is_valid = len(errors) == 0

    if is_valid:
        logger.info(f"Validation passed for command: {cmd}")
    else:
        logger.warning(f"Validation failed: {errors}")

    return {
        "is_valid": is_valid,
        "validation_errors": errors,
    }


def validator_router(state: HackerGraphState) -> Literal["valid", "invalid"]:
    """Router function to determine next step after validation."""
    is_valid = state.get("is_valid", False)
    retry_count = state.get("compiler_retry_count", 0)

    # Check if we've exceeded max retries
    if not is_valid and retry_count >= config.MAX_COMPILER_RETRIES:
        logger.error(f"Max compiler retries ({config.MAX_COMPILER_RETRIES}) exceeded")
        # We'll treat this as "valid" to move to executor which will handle the error
        # Alternatively, you could add a "max_retries_exceeded" path
        return "valid"  # Let executor handle the error state

    if is_valid:
        return "valid"
    return "invalid"
