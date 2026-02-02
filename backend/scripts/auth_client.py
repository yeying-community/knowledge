#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from eth_account import Account
from eth_account.messages import encode_defunct


def http_json(
    method: str,
    url: str,
    payload: Dict[str, Any] | None = None,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> Tuple[int, Any]:
    data = None
    merged = {"Content-Type": "application/json"}
    if headers:
        merged.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, raw or e.reason


def _extract_nested(payload: Any, *path: str) -> Any:
    cur = payload
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def extract_challenge(payload: Any) -> Optional[str]:
    val = _extract_nested(payload, "data", "challenge")
    if isinstance(val, str):
        return val
    val2 = _extract_nested(payload, "challenge")
    return val2 if isinstance(val2, str) else None


def extract_token(payload: Any) -> Optional[str]:
    val = _extract_nested(payload, "data", "token")
    if isinstance(val, str):
        return val
    val2 = _extract_nested(payload, "token")
    return val2 if isinstance(val2, str) else None


def login_with_private_key(api_base: str, private_key: str, *, timeout: int = 10) -> Tuple[str, str]:
    """
    SIWE-like login via /api/v1/public/auth/challenge + /verify.
    Returns (address, access_token).
    """
    api_base = api_base.rstrip("/")
    pk = private_key.strip()
    if pk.startswith("0x"):
        pk = pk[2:]
    acct = Account.from_key(pk)
    address = acct.address.lower()

    st, ch = http_json(
        "POST",
        f"{api_base}/api/v1/public/auth/challenge",
        {"address": address},
        timeout=timeout,
    )
    if st >= 400:
        raise RuntimeError(f"auth challenge failed: {st} {ch}")
    challenge = extract_challenge(ch)
    if not challenge:
        raise RuntimeError("auth challenge response missing challenge")

    signed = Account.sign_message(encode_defunct(text=challenge), private_key=pk)
    signature = signed.signature.hex()

    st2, ver = http_json(
        "POST",
        f"{api_base}/api/v1/public/auth/verify",
        {"address": address, "signature": signature},
        timeout=timeout,
    )
    if st2 >= 400:
        raise RuntimeError(f"auth verify failed: {st2} {ver}")
    token = extract_token(ver)
    if not token:
        raise RuntimeError("auth verify response missing token")
    return address, token


def resolve_test_private_key(cli_value: Optional[str] = None) -> Optional[str]:
    return (cli_value or os.getenv("RAG_TEST_PRIVATE_KEY") or "").strip() or None


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

