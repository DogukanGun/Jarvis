"""
Shared normalization utilities

Used by mem0 and episode retrieval nodes.
"""

from typing import Any, List


def normalize_mem0_items(data: Any) -> List[dict]:
    """
    Normalize mem0 response data into a stable list of dict items.

    The mem0 API returns data in various formats:
    - List of memory objects
    - Dict with memories under a key (memories/items/results/data)
    - Single memory object
    - None or empty

    Args:
        data: Raw data from mem0 API response

    Returns:
        List of memory dict objects (always returns a list, never None)
    """
    if data is None:
        return []

    if isinstance(data, list):
        return _normalize_list(data)

    if isinstance(data, dict):
        # Try common keys that might contain the memories list
        for key in ("memories", "items", "results", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return _normalize_list(value)

        # Check if the dict itself is a single memory object
        # Look for common memory fields
        memory_indicators = ("text", "content", "memory", "message", "id")
        if any(k in data for k in memory_indicators):
            return [data]

        # Empty dict or unrecognized structure
        return []

    # Other types (str, int, etc.) - ignore
    return []


def _normalize_list(lst: List[Any]) -> List[dict]:
    """
    Normalize a list to contain only valid memory items.

    Args:
        lst: List of items (could be dicts, strings, or other)

    Returns:
        List of dict items
    """
    out = []
    for item in lst:
        if isinstance(item, dict):
            # Dict items are kept as-is
            out.append(item)
        elif isinstance(item, str) and item.strip():
            # String items are wrapped in a dict
            out.append({"text": item})
        # Ignore other types (None, int, etc.)

    return out


def safe_str(value: Any, max_length: int = 200) -> str:
    """
    Safely convert any value to string for logging.

    Args:
        value: Value to convert
        max_length: Maximum length of output string

    Returns:
        String representation, truncated if needed
    """
    try:
        s = str(value)
        if len(s) > max_length:
            return s[:max_length] + "..."
        return s
    except Exception:
        return "<unable to convert to string>"
