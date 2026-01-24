#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def http_json(
    method: str,
    url: str,
    payload: Dict[str, Any] | None = None,
    *,
    timeout: int = 10,
) -> Tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, raw or e.reason


def ensure_app_registered(api_base: str, app_id: str, wallet_id: str, timeout: int) -> None:
    status, body = http_json(
        "POST",
        f"{api_base}/app/register",
        {"app_id": app_id, "wallet_id": wallet_id},
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/app/register failed: {status} {body}")


def check_stores_health(api_base: str, timeout: int) -> Dict[str, Any]:
    status, body = http_json("GET", f"{api_base}/stores/health", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/stores/health failed: {status} {body}")
    return body or {}


def upload_jd(
    api_base: str,
    wallet_id: str,
    app_id: str,
    jd_payload: Dict[str, Any],
    timeout: int,
    *,
    session_id: str = "",
    jd_id: str = "",
    kb_key: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "wallet_id": wallet_id,
        "app_id": app_id,
        "jd": jd_payload,
    }
    if session_id:
        payload["session_id"] = session_id
    if jd_id:
        payload["jd_id"] = jd_id
    if kb_key:
        payload["kb_key"] = kb_key
    if metadata:
        payload["metadata"] = metadata

    status, body = http_json("POST", f"{api_base}/{app_id}/jd/upload", payload, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/{app_id}/jd/upload failed: {status} {body}")
    return body or {}


def run_query_with_jd_id(
    api_base: str,
    wallet_id: str,
    app_id: str,
    session_id: str,
    jd_id: str,
    timeout: int,
    *,
    target: str = "",
    company: str = "",
) -> Dict[str, Any]:
    payload = {
        "wallet_id": wallet_id,
        "app_id": app_id,
        "session_id": session_id,
        "intent": "generate_questions",
        "jd_id": jd_id,
        "target": target,
        "company": company,
        "intent_params": {
            "basic_count": 2,
            "project_count": 2,
            "scenario_count": 1,
        },
    }
    status, body = http_json("POST", f"{api_base}/query", payload, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/query failed: {status} {body}")
    return body or {}


def load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="JD upload + jd_id query smoke test")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--app-id", default="interviewer", help="App ID")
    parser.add_argument("--wallet-id", default="wallet_demo", help="Wallet ID")
    parser.add_argument("--session-id", default="session_jd_001", help="Session ID")
    parser.add_argument("--jd-id", default="", help="Optional JD ID for upload")
    parser.add_argument("--kb-key", default="", help="Optional user_upload KB key")
    parser.add_argument("--jd-file", default="", help="Optional local JD JSON file")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--skip-query", action="store_true", help="Skip /query calls")
    parser.add_argument("--skip-health", action="store_true", help="Skip /stores/health preflight")
    parser.add_argument("--skip-default", action="store_true", help="Skip missing jd_id fallback query")
    parser.add_argument("--target", default="backend engineer", help="Target role for default query")
    parser.add_argument("--company", default="", help="Company name for default query")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    wallet_id = args.wallet_id
    app_id = args.app_id
    session_id = args.session_id
    timeout = args.timeout

    testdata_dir = Path(__file__).resolve().parent / "testdata"
    jd_path = Path(args.jd_file) if args.jd_file else testdata_dir / "jd.json"
    jd_payload = load_json_file(jd_path)

    print("== JD Upload + JD ID Smoke Test ==")
    print(f"API Base: {api_base}")
    print(f"Identity: wallet={wallet_id} app={app_id} session={session_id}")

    if not args.skip_health:
        print("\n[0/3] Stores health check")
        health = check_stores_health(api_base, timeout)
        for item in health.get("stores", []):
            name = str(item.get("name", "-")).upper()
            status = item.get("status", "-")
            detail = item.get("details", "")
            print(f"- {name}: {status} {detail}")

    print("\n[1/3] Register app")
    ensure_app_registered(api_base, app_id, wallet_id, timeout)
    print("OK")

    print(f"\n[2/3] Upload JD via /{app_id}/jd/upload")
    upload_resp = upload_jd(
        api_base,
        wallet_id,
        app_id,
        jd_payload,
        timeout,
        session_id=session_id,
        jd_id=args.jd_id,
        kb_key=args.kb_key,
        metadata={"source": "smoke"},
    )
    print(json.dumps(upload_resp, ensure_ascii=False, indent=2))

    if args.skip_query:
        return 0

    jd_id = upload_resp.get("jd_id") or args.jd_id
    if jd_id:
        print("\n[3/3] Query with jd_id (no query)")
        answer = run_query_with_jd_id(
            api_base,
            wallet_id,
            app_id,
            session_id,
            jd_id,
            timeout,
            target=args.target,
            company=args.company,
        )
        print(json.dumps(answer, ensure_ascii=False, indent=2))

    if not args.skip_default:
        print("\n[default] Query with missing jd_id (fallback path)")
        missing_id = "missing_jd_id_demo"
        answer = run_query_with_jd_id(
            api_base,
            wallet_id,
            app_id,
            session_id,
            missing_id,
            timeout,
            target=args.target,
            company=args.company,
        )
        print(json.dumps(answer, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
