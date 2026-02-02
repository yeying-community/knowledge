# -*- coding: utf-8 -*-

from __future__ import annotations

import time
from typing import Any, Dict


def now_ms() -> int:
    return int(time.time() * 1000)


def ok(data: Any) -> Dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data, "timestamp": now_ms()}


def fail(code: int, message: str) -> Dict[str, Any]:
    return {"code": int(code), "message": str(message), "data": None, "timestamp": now_ms()}

