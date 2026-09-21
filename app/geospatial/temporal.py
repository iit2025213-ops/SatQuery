"""Temporal validation for remote-sensing sequences.

Deterministic checks for temporal ordering and interval calculation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def parse_timestamp(ts: str | datetime | None) -> datetime | None:
    """Safely parse a timestamp into a datetime object."""
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        # Assuming ISO 8601 string format
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Failed to parse timestamp: %s", ts)
        return None


def validate_temporal_ordering(t1: str | datetime | None, t2: str | datetime | None) -> dict[str, Any]:
    """Deterministically check that T1 strictly precedes T2."""
    dt1 = parse_timestamp(t1)
    dt2 = parse_timestamp(t2)
    
    if not dt1 or not dt2:
        return {
            "valid": False,
            "status": "UNKNOWN_TIMESTAMP",
            "reason": "Missing or unparseable timestamp(s)"
        }
        
    if dt1 < dt2:
        interval_days = (dt2 - dt1).days
        return {
            "valid": True,
            "status": "VALID",
            "interval_days": interval_days,
            "t1": dt1.isoformat(),
            "t2": dt2.isoformat()
        }
    elif dt1 == dt2:
        return {
            "valid": False,
            "status": "INVALID",
            "reason": "Timestamps are identical (T1 == T2)"
        }
    else:
        return {
            "valid": False,
            "status": "INVALID",
            "reason": "Reversed temporal ordering (T2 precedes T1)"
        }
