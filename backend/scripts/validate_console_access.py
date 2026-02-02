#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from auth_client import auth_headers, login_with_private_key, resolve_test_private_key, http_json


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    payload: Any | None = None


def check_health(api_base: str, timeout: int) -> CheckResult:
    status, body = http_json("GET", f"{api_base}/health", timeout=timeout)
    if status >= 400:
        return CheckResult("health", False, f"{status} {body}")
    return CheckResult("health", True, payload=body)


def register_app(api_base: str, app_id: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json(
        "POST",
        f"{api_base}/app/register",
        {"app_id": app_id, "wallet_id": wallet_id},
        headers=headers,
        timeout=timeout,
    )
    if status >= 400:
        return CheckResult("app.register", False, f"{status} {body}")
    return CheckResult("app.register", True, payload=body)


def list_apps(api_base: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json("GET", f"{api_base}/app/list?wallet_id={wallet_id}", headers=headers, timeout=timeout)
    if status >= 400:
        return CheckResult("app.list", False, f"{status} {body}")
    return CheckResult("app.list", True, payload=body or [])


def app_status(api_base: str, app_id: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json(
        "GET",
        f"{api_base}/app/{app_id}/status?wallet_id={wallet_id}",
        headers=headers,
        timeout=timeout,
    )
    if status >= 400:
        return CheckResult("app.status", False, f"{status} {body}")
    return CheckResult("app.status", True, payload=body)


def kb_list(api_base: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json("GET", f"{api_base}/kb/list?wallet_id={wallet_id}", headers=headers, timeout=timeout)
    if status >= 400:
        return CheckResult("kb.list", False, f"{status} {body}")
    return CheckResult("kb.list", True, payload=body or [])


def kb_stats(api_base: str, app_id: str, kb_key: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json(
        "GET",
        f"{api_base}/kb/{app_id}/{kb_key}/stats?wallet_id={wallet_id}",
        headers=headers,
        timeout=timeout,
    )
    if status >= 400:
        return CheckResult("kb.stats", False, f"{status} {body}")
    return CheckResult("kb.stats", True, payload=body)


def ingestion_logs(api_base: str, app_id: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json(
        "GET",
        f"{api_base}/ingestion/logs?wallet_id={wallet_id}&app_id={app_id}&limit=5",
        headers=headers,
        timeout=timeout,
    )
    if status >= 400:
        return CheckResult("ingestion.logs", False, f"{status} {body}")
    return CheckResult("ingestion.logs", True, payload=body)


def super_admin_list(api_base: str, wallet_id: str, timeout: int, headers: Dict[str, str] | None = None) -> CheckResult:
    status, body = http_json("GET", f"{api_base}/app/list?wallet_id={wallet_id}", headers=headers, timeout=timeout)
    if status >= 400:
        return CheckResult("super_admin.list", False, f"{status} {body}")
    return CheckResult("super_admin.list", True, payload=body or [])


def format_payload(payload: Any) -> str:
    if payload is None:
        return ""
    try:
        text = json.dumps(payload, ensure_ascii=False)
    except Exception:
        text = str(payload)
    return text if len(text) <= 320 else f"{text[:320]}..."


def print_results(results: List[CheckResult]) -> None:
    for res in results:
        mark = "OK " if res.ok else "FAIL"
        detail = f" {res.detail}" if res.detail else ""
        payload = format_payload(res.payload)
        payload_str = f" payload={payload}" if payload else ""
        print(f"[{mark}] {res.name}{detail}{payload_str}")

    total = len(results)
    passed = len([r for r in results if r.ok])
    print(f"\nSummary: {passed}/{total} passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tenant console access and app status APIs.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--wallet-id", default="wallet_demo", help="Tenant wallet ID")
    parser.add_argument("--private-key", default="", help="Optional EVM private key for SIWE login (or env RAG_TEST_PRIVATE_KEY)")
    parser.add_argument("--app-id", default="interviewer", help="App ID")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds")
    parser.add_argument(
        "--super-admin-id",
        default=os.getenv("SUPER_ADMIN_WALLET_ID", ""),
        help="Optional super admin wallet ID for cross-tenant checks",
    )
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    wallet_id = args.wallet_id
    app_id = args.app_id
    timeout = args.timeout
    headers = None

    private_key = resolve_test_private_key(args.private_key)
    if private_key:
        addr, token = login_with_private_key(api_base, private_key, timeout=timeout)
        if args.wallet_id and args.wallet_id != "wallet_demo" and args.wallet_id.lower() != addr.lower():
            print("ERROR: --wallet-id does not match the provided --private-key address", file=sys.stderr)
            return 2
        wallet_id = addr
        headers = auth_headers(token)

    results: List[CheckResult] = []
    results.append(check_health(api_base, timeout))
    results.append(register_app(api_base, app_id, wallet_id, timeout, headers=headers))

    app_list_res = list_apps(api_base, wallet_id, timeout, headers=headers)
    results.append(app_list_res)
    results.append(app_status(api_base, app_id, wallet_id, timeout, headers=headers))

    kb_res = kb_list(api_base, wallet_id, timeout, headers=headers)
    results.append(kb_res)

    if kb_res.ok and isinstance(kb_res.payload, list):
        kb_match = next(
            (kb for kb in kb_res.payload if kb.get("app_id") == app_id and kb.get("kb_key")),
            None,
        )
        if kb_match:
            results.append(
                kb_stats(
                    api_base,
                    app_id,
                    str(kb_match.get("kb_key")),
                    wallet_id,
                    timeout,
                    headers=headers,
                )
            )
        else:
            results.append(CheckResult("kb.stats", True, "skipped (no kb found for app)"))

    results.append(ingestion_logs(api_base, app_id, wallet_id, timeout, headers=headers))

    super_admin_id = (args.super_admin_id or "").strip()
    if super_admin_id and super_admin_id != wallet_id:
        results.append(super_admin_list(api_base, super_admin_id, timeout, headers=headers))

    print_results(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
