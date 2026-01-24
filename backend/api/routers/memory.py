# api/routers/memory.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
import hashlib
import json
from typing import Optional

from api.schemas.memory import (
    MemoryPushRequest,
    MemoryPushResponse,
    MemorySessionList,
    MemoryContextList,
    MemoryContextUpdateRequest,
    MemoryContextItem,
)
from api.routers.owner import ensure_app_owner, is_super_admin, require_wallet_id

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/push", response_model=MemoryPushResponse)
def push_memory(req: MemoryPushRequest, deps=Depends(get_deps)):
    try:
        row = deps.datasource.app_store.get(req.app_id)
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"app_id={req.app_id} not active in DB")

        identity = deps.identity_manager.resolve_identity(
            wallet_id=req.wallet_id,
            app_id=req.app_id,
            session_id=req.session_id,
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


def _attach_memory_content(rows: list[dict], deps, *, limit_chars: Optional[int] = None) -> list[dict]:
    if not rows:
        return rows
    if not deps.datasource.minio:
        return rows
    bucket = deps.datasource.bucket
    json_cache: dict[str, dict] = {}
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
        for msg in data.get("messages", []):
            content = msg.get("content", "")
            if not content:
                continue
            if hashlib.sha256(content.encode("utf-8")).hexdigest() == sha:
                row["content"] = content if not limit_chars else content[:limit_chars]
                break
    return rows


@router.get("/sessions", response_model=MemorySessionList)
def list_memory_sessions(
    app_id: Optional[str] = None,
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    deps=Depends(get_deps),
):
    try:
        wallet_id = require_wallet_id(wallet_id)
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


@router.get("/{memory_key}/contexts", response_model=MemoryContextList)
def list_memory_contexts(
    memory_key: str,
    wallet_id: Optional[str] = None,
    data_wallet_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    include_content: int = 0,
    deps=Depends(get_deps),
):
    try:
        operator_wallet = require_wallet_id(wallet_id)
        meta = deps.datasource.memory_metadata.get(memory_key)
        if not meta:
            raise HTTPException(status_code=404, detail="memory session not found")
        ensure_app_owner(deps, meta.get("app_id"), operator_wallet)
        if data_wallet_id and meta.get("wallet_id") != data_wallet_id:
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
    data_wallet_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    try:
        operator_wallet = require_wallet_id(wallet_id)
        row = deps.datasource.memory_contexts.get(uid)
        if not row:
            raise HTTPException(status_code=404, detail="memory context not found")
        meta = deps.datasource.memory_metadata.get(row.get("memory_key"))
        if not meta:
            raise HTTPException(status_code=404, detail="memory session not found")
        ensure_app_owner(deps, meta.get("app_id"), operator_wallet)
        if data_wallet_id and meta.get("wallet_id") != data_wallet_id:
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
