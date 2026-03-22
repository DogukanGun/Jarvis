"""Reusable output-parser utilities for structured extraction from tool output."""

import json
import re
from typing import Any, Dict, List, Optional


class RegexTableParser:
    """Parses tabular text output by applying a regex pattern to each line."""

    @staticmethod
    def parse(
        text: str, pattern: str, field_names: List[str]
    ) -> List[Dict[str, str]]:
        """Apply *pattern* to every line and map captured groups to *field_names*.

        Args:
            text: Multi-line raw text to parse.
            pattern: A regex with capturing groups (one per field name).
            field_names: Names to assign to each captured group, in order.

        Returns:
            A list of dicts, one per matching line, keyed by *field_names*.
        """
        compiled = re.compile(pattern)
        results: List[Dict[str, str]] = []
        for line in text.splitlines():
            match = compiled.search(line)
            if match:
                groups = match.groups()
                entry = {
                    name: (groups[i] if i < len(groups) else "")
                    for i, name in enumerate(field_names)
                }
                results.append(entry)
        return results


class JsonOutputParser:
    """Extracts JSON objects or arrays from raw text output."""

    @staticmethod
    def parse(text: str) -> Optional[Any]:
        """Try to decode JSON from *text*.

        Strategy:
            1. Attempt ``json.loads`` on the full text.
            2. Fall back to locating the first ``{`` or ``[`` and parsing from there.
            3. Return ``None`` if no valid JSON is found.

        Args:
            text: Raw text that may contain JSON.

        Returns:
            The decoded Python object, or ``None`` on failure.
        """
        # Attempt 1: full text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Attempt 2: find first JSON-like substring
        for marker in ("{", "["):
            idx = text.find(marker)
            if idx == -1:
                continue
            # Determine the matching close character
            close = "}" if marker == "{" else "]"
            # Try progressively shorter substrings from the end
            substring = text[idx:]
            last_close = substring.rfind(close)
            while last_close != -1:
                candidate = substring[: last_close + 1]
                try:
                    return json.loads(candidate)
                except (json.JSONDecodeError, TypeError, ValueError):
                    last_close = substring.rfind(close, 0, last_close)

        return None


class KeyValueParser:
    """Parses key-value lines separated by a configurable delimiter."""

    @staticmethod
    def parse(text: str, separator: str = ":") -> Dict[str, str]:
        """Split each non-empty line on *separator* and collect key-value pairs.

        The first occurrence of *separator* is used as the split point so that
        values containing the separator are preserved.

        Args:
            text: Multi-line raw text.
            separator: Character(s) to split on (default ``":"``).

        Returns:
            A dict mapping stripped keys to stripped values.
        """
        result: Dict[str, str] = {}
        for line in text.splitlines():
            if separator not in line:
                continue
            key, _, value = line.partition(separator)
            key = key.strip()
            value = value.strip()
            if key:
                result[key] = value
        return result


class SeverityExtractor:
    """Extracts lines tagged with common severity/status markers."""

    # Ordered from most to least severe; bracket-style markers come first.
    _MARKERS = {
        "[CRITICAL]": "CRITICAL",
        "[WARNING]": "WARNING",
        "[INFO]": "INFO",
        "[OK]": "OK",
        "[!]": "CRITICAL",
        "[+]": "OK",
        "[*]": "INFO",
        "[-]": "WARNING",
    }

    @classmethod
    def extract(cls, text: str) -> List[Dict[str, str]]:
        """Scan *text* for severity markers and return structured findings.

        Recognised markers (case-sensitive):
            ``[CRITICAL]``, ``[WARNING]``, ``[INFO]``, ``[OK]``,
            ``[!]``, ``[+]``, ``[*]``, ``[-]``

        Args:
            text: Multi-line raw text.

        Returns:
            A list of ``{"severity": ..., "message": ...}`` dicts, one per
            matching line, in the order they appear.
        """
        results: List[Dict[str, str]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            for marker, severity in cls._MARKERS.items():
                if marker in stripped:
                    # Remove the marker from the message for cleanliness
                    message = stripped.replace(marker, "", 1).strip()
                    results.append({"severity": severity, "message": message})
                    break  # first matching marker wins
        return results
