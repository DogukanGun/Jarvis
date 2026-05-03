"""Atomic JSON persistence for tracked positions.

The runner keeps positions in `_positions: Dict[str, TrackedPosition]` in
memory. If the strategy process crashes or is killed, that dict vanishes
and we lose track of held tokens that still need selling.

This module persists the dict to a single JSON file alongside the runner
and reloads it on startup. Atomic writes via `os.replace` so a crash
during write can't leave a half-written file.

File location: `<strategy_cwd>/.auto-positions.json`
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_PATH = Path(".auto-positions.json")


def _store_path() -> Path:
    return _PATH.resolve()


def save(positions: Dict[str, Any], policy_id: Optional[str]) -> None:
    """Serialise positions to disk atomically.

    `positions` is the runner's `_positions` dict mapping mint → TrackedPosition.
    """
    payload: Dict[str, Any] = {
        "version": SCHEMA_VERSION,
        "policy_id": policy_id,
        "saved_at": datetime.utcnow().isoformat(),
        "positions": [_pos_to_dict(p) for p in positions.values()],
    }
    target = _store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".auto-positions-", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def load() -> Optional[Dict[str, Any]]:
    """Return the persisted payload, or None if no/invalid store."""
    target = _store_path()
    if not target.exists():
        return None
    try:
        with target.open("r") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("auto-positions store unreadable, ignoring: %s", e)
        return None
    if payload.get("version") != SCHEMA_VERSION:
        logger.warning(
            "auto-positions store version %s != %s, ignoring",
            payload.get("version"), SCHEMA_VERSION,
        )
        return None
    return payload


def clear() -> None:
    """Remove the persisted file (called after a clean drain or hard stop)."""
    target = _store_path()
    try:
        if target.exists():
            target.unlink()
    except OSError as e:
        logger.warning("auto-positions clear failed: %s", e)


# ── Conversion helpers ────────────────────────────────────────────────────────


def _pos_to_dict(p: Any) -> Dict[str, Any]:
    """TrackedPosition → JSON-safe dict. We import lazily / duck-type to
    avoid a circular import with runner."""
    inner = p.inner
    return {
        "mint": inner.mint,
        "symbol": inner.symbol,
        "entry_price": inner.entry_price,
        "quantity": inner.quantity,
        "entry_time_iso": inner.entry_time.isoformat() if inner.entry_time else None,
        "take_profit_price": inner.take_profit_price,
        "stop_loss_price": inner.stop_loss_price,
        "max_hold_time": inner.max_hold_time,
        "is_active": inner.is_active,
        "exit_reason": inner.exit_reason.value if inner.exit_reason else None,
        "exit_price": inner.exit_price,
        "exit_time_iso": inner.exit_time.isoformat() if inner.exit_time else None,
        "entry_sol": p.entry_sol,
        "sell_attempted": p.sell_attempted,
        "sold": p.sold,
        "last_error": p.last_error,
    }


def positions_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the raw list of position dicts from a loaded payload."""
    return list(payload.get("positions") or [])
