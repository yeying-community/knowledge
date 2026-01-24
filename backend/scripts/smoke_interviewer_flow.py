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

from settings.config import Settings
from datasource.connections.minio_connection import MinioConnection
from datasource.objectstores.minio_store import MinIOStore
from datasource.objectstores.path_builder import PathBuilder
from identity.identity_manager import IdentityManager
from identity.models import Identity


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


def upload_session_to_minio(
    wallet_id: str,
    app_id: str,
    session_id: str,
    filename: str,
    payload: Dict[str, Any],
) -> str:
    settings = Settings()
    if not settings.minio_enabled:
        raise RuntimeError("MINIO is disabled. Check MINIO_ENABLED.")

    if not settings.minio_access_key or not settings.minio_secret_key:
        raise RuntimeError("MINIO credentials missing.")

    minio = MinIOStore(
        MinioConnection(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    )

    memory_key = IdentityManager.generate_memory_key(wallet_id, app_id, session_id)
    identity = Identity(
        wallet_id=wallet_id,
        app_id=app_id,
        session_id=session_id,
        memory_key=memory_key,
    )
    key = PathBuilder.business_file(identity, filename)
    minio.put_json(settings.minio_bucket, key, payload)
    return f"{settings.minio_bucket}/{key}"


def push_memory(
    api_base: str,
    wallet_id: str,
    app_id: str,
    session_id: str,
    filename: str,
    description: str,
    timeout: int,
) -> Dict[str, Any]:
    status, body = http_json(
        "POST",
        f"{api_base}/memory/push",
        {
            "wallet_id": wallet_id,
            "app_id": app_id,
            "session_id": session_id,
            "filename": filename,
            "description": description,
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/memory/push failed: {status} {body}")
    return body or {}


def run_query(
    api_base: str,
    wallet_id: str,
    app_id: str,
    session_id: str,
    query: str,
    timeout: int,
) -> Dict[str, Any]:
    status, body = http_json(
        "POST",
        f"{api_base}/query",
        {
            "wallet_id": wallet_id,
            "app_id": app_id,
            "session_id": session_id,
            "intent": "generate_questions",
            "query": query,
            "intent_params": {
                "basic_count": 3,
                "project_count": 2,
                "scenario_count": 2,
                "target_position": "后端工程师",
            },
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/query failed: {status} {body}")
    return body or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Interview flow smoke test")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--app-id", default="interviewer", help="App ID")
    parser.add_argument("--wallet-id", default="wallet_demo", help="Wallet ID")
    parser.add_argument("--session-id", default="session_demo_001", help="Session ID")
    parser.add_argument("--filename", default="history/session_demo.json", help="Session JSON filename in MinIO")
    parser.add_argument("--session-file", default="", help="Optional local session JSON file path")
    parser.add_argument("--skip-query", action="store_true", help="Skip /query call")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--skip-health", action="store_true", help="Skip /stores/health preflight")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    wallet_id = args.wallet_id
    app_id = args.app_id
    session_id = args.session_id
    filename = args.filename
    timeout = args.timeout

    session_payload = {
        "messages": [
            {"role": "assistant", "content": "Hi, I am the interviewer. Let's start with a short technical chat."},
            {"role": "user", "content": "I have been working on distributed scheduling and retries."},
            {"role": "assistant", "content": "How do you keep tasks idempotent and consistent?"},
            {"role": "user", "content": "I use idempotency keys and a state machine with a de-dup queue."},
            {"role": "assistant", "content": "How do you handle partial failures or duplicated events?"},
            {"role": "user", "content": "I use compensating actions and record failure reasons for replay."},
        ]
    }
    if args.session_file:
        with open(args.session_file, "r", encoding="utf-8") as f:
            session_payload = json.load(f)

    print("== Interviewer Flow Smoke Test ==")
    print(f"API Base: {api_base}")
    print(f"Identity: wallet={wallet_id} app={app_id} session={session_id}")

    if not args.skip_health:
        print("\n[0/4] Stores health check")
        health = check_stores_health(api_base, timeout)
        stores = health.get("stores", [])
        if not stores:
            print("No stores reported.")
        else:
            for item in stores:
                name = str(item.get("name", "-")).upper()
                status = item.get("status", "-")
                detail = item.get("details", "")
                print(f"- {name}: {status} {detail}")

    print("\n[1/4] Register app")
    ensure_app_registered(api_base, app_id, wallet_id, timeout)
    print("OK")

    print("\n[2/4] Upload session history to MinIO")
    minio_key = upload_session_to_minio(wallet_id, app_id, session_id, filename, session_payload)
    print(f"OK: {minio_key}")

    print("\n[3/4] Push memory")
    result = push_memory(
        api_base,
        wallet_id,
        app_id,
        session_id,
        filename,
        description="interviewer session history",
        timeout=timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.skip_query:
        print("\n[4/4] Skip query")
        return 0

    print("\n[4/4] Query with memory context")
    answer = run_query(
        api_base,
        wallet_id,
        app_id,
        session_id,
        query="Based on the earlier conversation, propose deeper follow-up questions.",
        timeout=timeout,
    )
    print(json.dumps(answer, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
