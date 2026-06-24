"""
Tracks which Certificate IDs have already been used for a successful
credit transfer, to prevent a student reusing the same genuine
certificate twice. Uses a simple JSON file for now -- swap this for a
real DB table (e.g. `used_certificates(certificate_id PK, student_roll,
used_at)`) once this integrates with the EMS database.
"""

import json
import os
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

_lock = Lock()


def _load(store_path: str) -> dict:
    if not os.path.exists(store_path):
        return {}
    with open(store_path, "r") as f:
        return json.load(f)


def _save(data: dict, store_path: str):
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "w") as f:
        json.dump(data, f, indent=2)


def is_certificate_used(certificate_id: str, store_path: str) -> bool:
    with _lock:
        data = _load(store_path)
    return certificate_id in data


def get_usage_info(certificate_id: str, store_path: str) -> Optional[dict]:
    with _lock:
        data = _load(store_path)
    return data.get(certificate_id)


def mark_certificate_used(certificate_id: str, student_roll: str, store_path: str):
    with _lock:
        data = _load(store_path)
        data[certificate_id] = {
            "used_by": student_roll,
            "used_at": datetime.now(timezone.utc).isoformat(),
        }
        _save(data, store_path)
