# api/routers/memory.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from api.deps import get_deps
import hashlib
import json
from typing import Optional

from api.schemas.memory import (
    MemoryPushRequest,
    MemoryPushResponse,
    MemoryUploadResponse,
    MemoryDeleteResponse,
    MemorySessionList,
    MemoryContextList,
    MemoryContextUpdateRequest,
    MemoryContextItem,
)
from api.routers.owner import ensure_app_owner, ensure_can_act_for_data_wallet, is_super_admin, require_wallet_id
from api.auth.deps import get_optional_auth_wallet_id, resolve_operator_wallet_id
from api.auth.normalize import normalize_wallet_id
from datasource.objectstores.path_builder import PathBuilder
from core.memory.auxiliary_memory import AuxiliaryMemory

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/push", response_model=MemoryPushResponse)
def push_memory(
    req: MemoryPushRequest,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        row = deps.datasource.app_store.get(req.app_id)
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"app_id={req.app_id} not active in DB")

        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=req.wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        data_wallet_id = normalize_wallet_id(req.data_wallet_id) or operator_wallet_id
        ensure_can_act_for_data_wallet(
            deps,
            app_id=req.app_id,
            operator_wallet_id=operator_wallet_id,
            data_wallet_id=data_wallet_id,
        )

        identity = deps.identity_manager.resolve_identity(
            wallet_id=operator_wallet_id,
            app_id=req.app_id,
            session_id=req.session_id,
            data_wallet_id=data_wallet_id,
        )

        summary_threshold = req.summary_threshold
        if summary_threshold is None:
            app_spec = deps.app_registry.get(req.app_id)
            memory_cfg = (app_spec.config or {}).get("memory", {}) or {}
            if "summary_threshold" in memory_cfg:
                try:
                    summary_threshold = int(memory_cfg.get("summary_threshold") or 0)
                except Exception:
                    summary_threshold = 0

        result = deps.memory_manager.push_session_file(
            identity=identity,
            filename=req.filename,
            description=req.description,
            summary_threshold=summary_threshold,
        )

        return MemoryPushResponse(**result)
    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_bool(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@router.post("/upload", response_model=MemoryUploadResponse)
def upload_memory(
    wallet_id: Optional[str] = Form(None),
    data_wallet_id: Optional[str] = Form(None),
    app_id: str = Form(...),
    session_id: str = Form(...),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    summary_threshold: Optional[int] = Form(None),
    run_push: Optional[str] = Form(None),
    file: UploadFile = File(...),
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        effective_data_wallet_id = normalize_wallet_id(data_wallet_id) or operator_wallet_id
        ensure_can_act_for_data_wallet(
            deps,
            app_id=app_id,
            operator_wallet_id=operator_wallet_id,
            data_wallet_id=effective_data_wallet_id,
        )
        if not deps.datasource.minio:
            raise HTTPException(status_code=400, detail="MinIO is not enabled")
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        identity = deps.identity_manager.resolve_identity(
            wallet_id=operator_wallet_id,
            app_id=app_id,
            session_id=session_id,
            data_wallet_id=effective_data_wallet_id,
        )

        raw = file.file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="empty file")

        safe_name = (filename or file.filename or "").strip() or "session_history.json"
        key = PathBuilder.business_file(identity, safe_name)
        deps.datasource.minio.put_bytes(
            bucket=deps.datasource.bucket,
            key=key,
            data=raw,
            content_type=file.content_type or "application/json",
        )
        sha256 = hashlib.sha256(raw).hexdigest()

        push_result = None
        if _parse_bool(run_push):
            push_result = deps.memory_manager.push_session_file(
                identity=identity,
                filename=safe_name,
                description=description,
                summary_threshold=summary_threshold,
            )

        return MemoryUploadResponse(
            bucket=deps.datasource.bucket,
            key=key,
            source_url=f"minio://{deps.datasource.bucket}/{key}",
            filename=safe_name,
            size_bytes=len(raw),
            content_sha256=sha256,
            data_wallet_id=effective_data_wallet_id,
            push_result=MemoryPushResponse(**push_result) if push_result else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _attach_memory_content(rows: list[dict], deps, *, limit_chars: Optional[int] = None) -> list[dict]:
    if not rows:
        return rows
    if not deps.datasource.minio:
        return rows
    bucket = deps.datasource.bucket
    json_cache: dict[str, dict] = {}

    def _msg_sha(url: str, idx: int, role: str, content: str) -> str:
        seed = f"{url}:{idx}:{role}:{content}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    for row in rows:
        url = row.get("url")
        sha = row.get("content_sha256")
        if not url or not sha:
            continue
        if url not in json_cache:
            raw = deps.datasource.minio.get_text(bucket=bucket, key=url)
            if not raw:
                json_cache[url] = {}
                continue
            try:
                json_cache[url] = json.loads(raw)
            except Exception:
                json_cache[url] = {}
                continue
        data = json_cache.get(url) or {}
        for idx, msg in enumerate(data.get("messages", [])):
            content = msg.get("content", "")
            if not content:
                continue
            role = msg.get("role", row.get("role") or "user")
            if _msg_sha(url, idx, str(role), content) == sha:
                row["content"] = content if not limit_chars else content[:limit_chars]
                break
    return rows


def _delete_memory_session_by_key(
    deps,
    *,
    memory_key: str,
    operator_wallet_id: str,
    expected_data_wallet_id: Optional[str] = None,
    delete_files: bool = False,
    delete_vectors: bool = True,
) -> MemoryDeleteResponse:
    sess = deps.datasource.identity_session.get_by_memory_key(memory_key)
    if not sess:
        raise HTTPException(status_code=404, detail="memory session not found")

    app_id = sess.get("app_id")
    owner_wallet_id = sess.get("wallet_id")
    ensure_can_act_for_data_wallet(
        deps,
        app_id=app_id,
        operator_wallet_id=operator_wallet_id,
        data_wallet_id=owner_wallet_id,
    )
    if expected_data_wallet_id and normalize_wallet_id(owner_wallet_id) != normalize_wallet_id(expected_data_wallet_id):
        raise HTTPException(status_code=404, detail="memory session not found")

    urls = deps.datasource.memory_contexts.list_urls_by_memory(memory_key)
    summary_url = None
    primary = deps.datasource.memory_primary.get(memory_key)
    if primary:
        summary_url = primary.get("summary_url")

    deleted_contexts = deps.datasource.memory_contexts.delete_by_memory(memory_key)
    deps.datasource.memory_primary.delete(memory_key)
    deps.datasource.memory_metadata.delete(memory_key)
    deleted_session = deps.datasource.identity_session.delete_by_memory_key(memory_key) > 0

    deleted_vectors = 0
    if delete_vectors and deps.datasource.weaviate:
        try:
            deleted_vectors = deps.datasource.weaviate.count(
                AuxiliaryMemory.COLLECTION_NAME,
                filters={"memory_key": memory_key},
            )
            deps.datasource.weaviate.delete_by_filter(
                AuxiliaryMemory.COLLECTION_NAME,
                {"memory_key": memory_key},
            )
        except Exception:
            deleted_vectors = 0

    deleted_files = 0
    if delete_files and deps.datasource.minio:
        bucket = deps.datasource.bucket
        candidates = set([url for url in urls if url])
        if summary_url:
            candidates.add(summary_url)
        for key in candidates:
            try:
                deps.datasource.minio.delete(bucket=bucket, key=key)
                deleted_files += 1
            except Exception:
                continue

    return MemoryDeleteResponse(
        status="ok",
        memory_key=memory_key,
        deleted_contexts=deleted_contexts,
        deleted_vectors=deleted_vectors,
        deleted_files=deleted_files,
        deleted_session=deleted_session,
    )


@router.get("/sessions", response_model=MemorySessionList)
def list_memory_sessions(
    app_id: Optional[str] = None,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    deps=Depends(get_deps),
):
    try:
        wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        if app_id:
            ensure_app_owner(deps, app_id, wallet_id)
        elif not is_super_admin(deps, wallet_id):
            raise HTTPException(status_code=400, detail="app_id is required")
        rows = deps.datasource.identity_session.list(
            app_id=app_id,
            wallet_id=data_wallet_id,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        total = deps.datasource.identity_session.count(
            app_id=app_id,
            wallet_id=data_wallet_id,
            session_id=session_id,
        )
        return MemorySessionList(items=rows, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions", response_model=MemoryDeleteResponse)
def delete_memory_session(
    app_id: str,
    session_id: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    delete_files: int = 0,
    delete_vectors: int = 1,
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        effective_data_wallet_id = normalize_wallet_id(data_wallet_id) or operator_wallet_id
        ensure_can_act_for_data_wallet(
            deps,
            app_id=app_id,
            operator_wallet_id=operator_wallet_id,
            data_wallet_id=effective_data_wallet_id,
        )
        row = deps.datasource.identity_session.get(effective_data_wallet_id, app_id, session_id)
        if not row:
            raise HTTPException(status_code=404, detail="memory session not found")
        memory_key = row.get("memory_key")
        return _delete_memory_session_by_key(
            deps,
            memory_key=memory_key,
            operator_wallet_id=operator_wallet_id,
            expected_data_wallet_id=effective_data_wallet_id,
            delete_files=bool(delete_files),
            delete_vectors=bool(delete_vectors),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{memory_key}", response_model=MemoryDeleteResponse)
def delete_memory_session_by_key(
    memory_key: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    delete_files: int = 0,
    delete_vectors: int = 1,
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        return _delete_memory_session_by_key(
            deps,
            memory_key=memory_key,
            operator_wallet_id=operator_wallet_id,
            expected_data_wallet_id=data_wallet_id,
            delete_files=bool(delete_files),
            delete_vectors=bool(delete_vectors),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_key}/contexts", response_model=MemoryContextList)
def list_memory_contexts(
    memory_key: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    include_content: int = 0,
    deps=Depends(get_deps),
):
    try:
        operator_wallet = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        sess = deps.datasource.identity_session.get_by_memory_key(memory_key)
        if not sess:
            raise HTTPException(status_code=404, detail="memory session not found")
        app_id = sess.get("app_id")
        owner_wallet_id = sess.get("wallet_id")
        ensure_can_act_for_data_wallet(
            deps,
            app_id=app_id,
            operator_wallet_id=operator_wallet,
            data_wallet_id=owner_wallet_id,
        )
        if data_wallet_id and normalize_wallet_id(owner_wallet_id) != normalize_wallet_id(data_wallet_id):
            raise HTTPException(status_code=404, detail="memory session not found")
        rows = deps.datasource.memory_contexts.list_by_memory(
            memory_key=memory_key,
            limit=limit,
            offset=offset,
        )
        if include_content:
            rows = _attach_memory_content(rows, deps, limit_chars=2000)
        total = deps.datasource.memory_contexts.count_by_memory(memory_key=memory_key)
        return MemoryContextList(items=rows, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/contexts/{uid}", response_model=MemoryContextItem)
def update_memory_context(
    uid: str,
    req: MemoryContextUpdateRequest,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    data_wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        operator_wallet = resolve_operator_wallet_id(
            request_wallet_id=wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        row = deps.datasource.memory_contexts.get(uid)
        if not row:
            raise HTTPException(status_code=404, detail="memory context not found")
        app_id = row.get("app_id")
        owner_wallet_id = row.get("wallet_id")
        ensure_can_act_for_data_wallet(
            deps,
            app_id=app_id,
            operator_wallet_id=operator_wallet,
            data_wallet_id=owner_wallet_id,
        )
        if data_wallet_id and normalize_wallet_id(owner_wallet_id) != normalize_wallet_id(data_wallet_id):
            raise HTTPException(status_code=404, detail="memory context not found")
        updated = deps.datasource.memory_contexts.update_fields(
            uid,
            description=req.description,
            role=req.role,
        )
        return MemoryContextItem(**(updated or row))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
