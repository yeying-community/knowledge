#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import weaviate.classes.config as wc

from settings.config import Settings
from datasource.connections.minio_connection import MinioConnection
from datasource.objectstores.minio_store import MinIOStore
from datasource.objectstores.path_builder import PathBuilder
from datasource.connections.weaviate_connection import WeaviateConnection
from datasource.vectorstores.weaviate_store import WeaviateStore
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


def check_health(api_base: str, timeout: int) -> None:
    status, body = http_json("GET", f"{api_base}/health", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/health failed: {status} {body}")
    print(json.dumps(body, ensure_ascii=False))


def check_stores(api_base: str, timeout: int) -> None:
    status, body = http_json("GET", f"{api_base}/stores/health", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/stores/health failed: {status} {body}")
    for item in body.get("stores", []):
        name = str(item.get("name", "-")).upper()
        status = item.get("status", "-")
        detail = item.get("details", "")
        print(f"- {name}: {status} {detail}")


def list_apps(api_base: str, wallet_id: str, timeout: int) -> list[dict]:
    status, body = http_json("GET", f"{api_base}/app/list?wallet_id={wallet_id}", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/app/list failed: {status} {body}")
    return body or []


def list_intents(api_base: str, app_id: str, timeout: int) -> dict:
    status, body = http_json("GET", f"{api_base}/app/{app_id}/intents", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/app/{app_id}/intents failed: {status} {body}")
    return body or {}


def list_kb(api_base: str, wallet_id: str, timeout: int) -> list[dict]:
    status, body = http_json("GET", f"{api_base}/kb/list?wallet_id={wallet_id}", timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/kb/list failed: {status} {body}")
    return body or []


def kb_stats(api_base: str, app_id: str, kb_key: str, wallet_id: str, timeout: int) -> dict:
    status, body = http_json(
        "GET",
        f"{api_base}/kb/{app_id}/{kb_key}/stats?wallet_id={wallet_id}",
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/stats failed: {status} {body}")
    return body or {}


def create_ingestion_log(api_base: str, app_id: str, kb_key: str, wallet_id: str, timeout: int) -> None:
    payload = {
        "wallet_id": wallet_id,
        "status": "success",
        "message": "smoke validation ingestion log",
        "app_id": app_id,
        "kb_key": kb_key,
        "collection": "",
        "meta": {"source": "smoke"},
    }
    status, body = http_json("POST", f"{api_base}/ingestion/logs", payload, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/ingestion/logs failed: {status} {body}")


def list_ingestion_logs(api_base: str, app_id: str, wallet_id: str, timeout: int) -> dict:
    status, body = http_json(
        "GET",
        f"{api_base}/ingestion/logs?wallet_id={wallet_id}&limit=5&app_id={app_id}",
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/ingestion/logs list failed: {status} {body}")
    return body or {}


def ensure_user_profile_collection(
    settings: Settings,
    collection: str,
    text_field: str,
    use_allowed_apps: bool,
) -> None:
    if not settings.weaviate_enabled:
        raise RuntimeError("WEAVIATE_ENABLED=false. Enable Weaviate for user uploads.")

    conn = WeaviateConnection(
        scheme=settings.weaviate_scheme,
        host=settings.weaviate_host,
        port=settings.weaviate_port,
        grpc_port=settings.weaviate_grpc_port,
        api_key=settings.weaviate_api_key,
    )
    store = WeaviateStore(conn)
    props = [
        wc.Property(name=text_field, data_type=wc.DataType.TEXT),
        wc.Property(name="wallet_id", data_type=wc.DataType.TEXT),
        wc.Property(name="resume_id", data_type=wc.DataType.TEXT),
        wc.Property(name="jd_id", data_type=wc.DataType.TEXT),
        wc.Property(name="source_url", data_type=wc.DataType.TEXT),
        wc.Property(name="metadata_json", data_type=wc.DataType.TEXT),
    ]
    if use_allowed_apps:
        props.append(wc.Property(name="allowed_apps", data_type=wc.DataType.TEXT))
    store.ensure_collection(collection, props)


def upload_to_minio(
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


def upload_resume_api(
    api_base: str,
    wallet_id: str,
    app_id: str,
    resume_payload: Dict[str, Any],
    timeout: int,
    *,
    session_id: str = "",
    resume_id: str = "",
    kb_key: str = "",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "wallet_id": wallet_id,
        "app_id": app_id,
        "resume": resume_payload,
    }
    if session_id:
        payload["session_id"] = session_id
    if resume_id:
        payload["resume_id"] = resume_id
    if kb_key:
        payload["kb_key"] = kb_key

    status, body = http_json("POST", f"{api_base}/resume/upload", payload, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/resume/upload failed: {status} {body}")
    return body or {}


def upload_jd_api(
    api_base: str,
    wallet_id: str,
    app_id: str,
    jd_payload: Dict[str, Any],
    timeout: int,
    *,
    session_id: str = "",
    jd_id: str = "",
    kb_key: str = "",
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

    status, body = http_json("POST", f"{api_base}/{app_id}/jd/upload", payload, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"/{app_id}/jd/upload failed: {status} {body}")
    return body or {}


def extract_resume_text(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("text", "content", "resume"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        segments = payload.get("segments")
        if isinstance(segments, list):
            return "\n".join(str(x) for x in segments if x)
        return json.dumps(payload)
    if isinstance(payload, list):
        return "\n".join(str(x) for x in payload if x)
    return str(payload or "")


def create_doc(
    api_base: str,
    app_id: str,
    kb_key: str,
    text: str,
    properties: Dict[str, Any],
    wallet_id: str,
    timeout: int,
) -> Dict[str, Any]:
    status, body = http_json(
        "POST",
        f"{api_base}/kb/{app_id}/{kb_key}/documents?wallet_id={wallet_id}",
        {"text": text, "properties": properties},
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/documents failed: {status} {body}")
    return body or {}


def replace_doc(
    api_base: str,
    app_id: str,
    kb_key: str,
    doc_id: str,
    text: str,
    properties: Dict[str, Any],
    wallet_id: str,
    timeout: int,
) -> Dict[str, Any]:
    status, body = http_json(
        "PUT",
        f"{api_base}/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id={wallet_id}",
        {"text": text, "properties": properties},
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/documents/{doc_id} put failed: {status} {body}")
    return body or {}


def patch_doc(
    api_base: str,
    app_id: str,
    kb_key: str,
    doc_id: str,
    properties: Dict[str, Any],
    wallet_id: str,
    timeout: int,
) -> Dict[str, Any]:
    status, body = http_json(
        "PATCH",
        f"{api_base}/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id={wallet_id}",
        {"properties": properties},
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/documents/{doc_id} patch failed: {status} {body}")
    return body or {}


def delete_doc(api_base: str, app_id: str, kb_key: str, doc_id: str, wallet_id: str, timeout: int) -> None:
    status, body = http_json(
        "DELETE",
        f"{api_base}/kb/{app_id}/{kb_key}/documents/{doc_id}?wallet_id={wallet_id}",
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/documents/{doc_id} delete failed: {status} {body}")


def list_docs(
    api_base: str,
    app_id: str,
    kb_key: str,
    timeout: int,
    *,
    wallet_id: str = "",
) -> dict:
    suffix = "?limit=5&offset=0"
    if wallet_id:
        suffix += f"&wallet_id={wallet_id}"
    status, body = http_json(
        "GET",
        f"{api_base}/kb/{app_id}/{kb_key}/documents{suffix}",
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/kb/{app_id}/{kb_key}/documents list failed: {status} {body}")
    return body or {}


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
    resume_url: str,
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
            "resume_url": resume_url,
            "intent_params": {
                "basic_count": 2,
                "project_count": 2,
                "scenario_count": 1,
                "target_position": "backend engineer",
            },
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/query failed: {status} {body}")
    return body or {}


def run_query_with_resume_id(
    api_base: str,
    wallet_id: str,
    app_id: str,
    session_id: str,
    resume_id: str,
    timeout: int,
    *,
    target: str = "",
    company: str = "",
) -> Dict[str, Any]:
    status, body = http_json(
        "POST",
        f"{api_base}/query",
        {
            "wallet_id": wallet_id,
            "app_id": app_id,
            "session_id": session_id,
            "intent": "generate_questions",
            "resume_id": resume_id,
            "target": target,
            "company": company,
            "intent_params": {
                "basic_count": 2,
                "project_count": 2,
                "scenario_count": 1,
            },
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/query failed: {status} {body}")
    return body or {}


def run_query_with_resume_and_jd_id(
    api_base: str,
    wallet_id: str,
    app_id: str,
    session_id: str,
    resume_id: str,
    jd_id: str,
    timeout: int,
    *,
    target: str = "",
    company: str = "",
) -> Dict[str, Any]:
    status, body = http_json(
        "POST",
        f"{api_base}/query",
        {
            "wallet_id": wallet_id,
            "app_id": app_id,
            "session_id": session_id,
            "intent": "generate_questions",
            "resume_id": resume_id,
            "jd_id": jd_id,
            "target": target,
            "company": company,
            "intent_params": {
                "basic_count": 2,
                "project_count": 2,
                "scenario_count": 1,
            },
        },
        timeout=timeout,
    )
    if status >= 400:
        raise RuntimeError(f"/query failed: {status} {body}")
    return body or {}


def load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Full RAG platform validation")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--app-id", default="interviewer", help="App ID")
    parser.add_argument("--wallet-id", default="wallet_demo", help="Wallet ID")
    parser.add_argument("--session-id", default="session_validation_001", help="Session ID")
    parser.add_argument("--kb-key", default="user_profile_kb", help="KB key for user upload")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds")
    parser.add_argument("--resume-file", default="", help="Resume JSON file path")
    parser.add_argument("--session-file", default="", help="Session history JSON file path")
    parser.add_argument("--jd-file", default="", help="JD JSON file path")
    parser.add_argument("--skip-query", action="store_true", help="Skip /query call")
    parser.add_argument("--skip-default", action="store_true", help="Skip missing resume_id fallback query")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    wallet_id = args.wallet_id
    app_id = args.app_id
    session_id = args.session_id
    kb_key = args.kb_key
    timeout = args.timeout

    testdata_dir = Path(__file__).resolve().parent / "testdata"
    resume_path = Path(args.resume_file) if args.resume_file else testdata_dir / "resume.json"
    session_path = Path(args.session_file) if args.session_file else testdata_dir / "session_history.json"
    resume_payload = load_json_file(resume_path)
    session_payload = load_json_file(session_path)
    jd_path = Path(args.jd_file) if args.jd_file else testdata_dir / "jd.json"
    jd_payload = load_json_file(jd_path)

    print("== Full RAG Validation ==")
    print(f"API Base: {api_base}")
    print(f"Identity: wallet={wallet_id} app={app_id} session={session_id}")

    print("\n[1/14] /health")
    check_health(api_base, timeout)

    print("\n[2/14] /stores/health")
    check_stores(api_base, timeout)

    print("\n[3/14] Register app")
    ensure_app_registered(api_base, app_id, wallet_id, timeout)
    print("OK")

    print("\n[4/14] App list + intents")
    apps = list_apps(api_base, wallet_id, timeout)
    intents = list_intents(api_base, app_id, timeout)
    print(json.dumps({"apps": apps, "intents": intents}, ensure_ascii=False, indent=2))

    print("\n[5/14] Ingestion logs")
    create_ingestion_log(api_base, app_id, kb_key, wallet_id, timeout)
    logs = list_ingestion_logs(api_base, app_id, wallet_id, timeout)
    print(json.dumps(logs, ensure_ascii=False, indent=2))

    print("\n[6/14] KB list + stats")
    kb_list = list_kb(api_base, wallet_id, timeout)
    kb_info = next((kb for kb in kb_list if kb.get("app_id") == app_id and kb.get("kb_key") == kb_key), None)
    if not kb_info:
        raise RuntimeError(f"KB not found for app_id={app_id} kb_key={kb_key}")
    stats = kb_stats(api_base, app_id, kb_key, wallet_id, timeout)
    print(json.dumps({"kb": kb_info, "stats": stats}, ensure_ascii=False, indent=2))

    print("\n[7/14] Upload resume via /resume/upload")
    upload_resp = upload_resume_api(
        api_base,
        wallet_id,
        app_id,
        resume_payload,
        timeout,
        session_id=session_id,
        kb_key=kb_key,
    )
    resume_id = upload_resp.get("resume_id") or ""
    resume_url = upload_resp.get("source_url") or ""
    print(json.dumps(upload_resp, ensure_ascii=False, indent=2))
    if not resume_id:
        raise RuntimeError("/resume/upload did not return resume_id")
    if not resume_url:
        raise RuntimeError("/resume/upload did not return source_url")

    print(f"\n[8/14] Upload JD via /{app_id}/jd/upload")
    jd_resp = upload_jd_api(
        api_base,
        wallet_id,
        app_id,
        jd_payload,
        timeout,
        session_id=session_id,
        kb_key=kb_key,
    )
    jd_id = jd_resp.get("jd_id") or ""
    jd_url = jd_resp.get("source_url") or ""
    print(json.dumps(jd_resp, ensure_ascii=False, indent=2))
    if not jd_id:
        raise RuntimeError(f"/{app_id}/jd/upload did not return jd_id")
    if not jd_url:
        raise RuntimeError(f"/{app_id}/jd/upload did not return source_url")

    print("\n[9/14] Ensure user_profile_kb collection")
    collection = kb_info.get("collection") or ""
    text_field = kb_info.get("text_field") or "text"
    use_allowed_apps = bool(kb_info.get("use_allowed_apps_filter"))
    ensure_user_profile_collection(Settings(), collection, text_field, use_allowed_apps)
    print(f"OK: {collection}")

    print("\n[10/14] KB document CRUD")
    resume_text = extract_resume_text(resume_payload)
    doc_id = str(uuid.uuid4())
    props = {
        text_field: resume_text,
        "wallet_id": wallet_id,
        "resume_id": doc_id,
        "source_url": resume_url,
        "metadata_json": json.dumps(resume_payload),
    }
    if use_allowed_apps:
        props["allowed_apps"] = app_id

    created = create_doc(api_base, app_id, kb_key, resume_text, props, wallet_id, timeout)
    replaced = replace_doc(
        api_base,
        app_id,
        kb_key,
        created.get("id", doc_id),
        resume_text,
        props,
        wallet_id,
        timeout,
    )
    patched = patch_doc(
        api_base,
        app_id,
        kb_key,
        created.get("id", doc_id),
        {"notes": "smoke validation"},
        wallet_id,
        timeout,
    )
    docs = list_docs(api_base, app_id, kb_key, timeout, wallet_id=wallet_id)
    print(json.dumps({"created": created, "replaced": replaced, "patched": patched, "docs": docs}, ensure_ascii=False, indent=2))

    print("\n[11/14] Upload session history to MinIO")
    session_key = upload_to_minio(wallet_id, app_id, session_id, "history/session.json", session_payload)
    print(f"OK: minio://{session_key}")

    print("\n[12/14] Push memory")
    memory_result = push_memory(
        api_base,
        wallet_id,
        app_id,
        session_id,
        "history/session.json",
        "validation session history",
        timeout,
    )
    print(json.dumps(memory_result, ensure_ascii=False, indent=2))

    if not args.skip_query:
        print("\n[13/14] Query with resume_id + jd_id (no query)")
        answer = run_query_with_resume_and_jd_id(
            api_base,
            wallet_id,
            app_id,
            session_id,
            resume_id,
            jd_id,
            timeout,
            target="backend engineer",
        )
        print(json.dumps(answer, ensure_ascii=False, indent=2))

        if not args.skip_default:
            print("\n[14/14] Query with missing jd_id (fallback path)")
            answer = run_query_with_resume_and_jd_id(
                api_base,
                wallet_id,
                app_id,
                session_id,
                resume_id,
                "missing_jd_id_demo",
                timeout,
                target="backend engineer",
            )
            print(json.dumps(answer, ensure_ascii=False, indent=2))

    print("\n[cleanup] Delete KB document")
    delete_doc(api_base, app_id, kb_key, created.get("id", doc_id), wallet_id, timeout)
    print("OK")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
