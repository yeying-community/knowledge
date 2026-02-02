# api/routers/private_dbs.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.routers.owner import ensure_app_owner, require_wallet_id, is_super_admin
from api.auth.deps import get_optional_auth_wallet_id, resolve_operator_wallet_id
from api.auth.normalize import normalize_wallet_id
from api.schemas.private_db import (
    PrivateDBBindRequest,
    PrivateDBBindResponse,
    PrivateDBCreateRequest,
    PrivateDBInfo,
    PrivateDBList,
    PrivateDBSessionInfo,
    PrivateDBSessionList,
    PrivateDBUnbindResponse,
)

router = APIRouter(prefix="/private_dbs", tags=["private-db"])


def _as_info(row) -> PrivateDBInfo:
    return PrivateDBInfo(
        private_db_id=row.get("private_db_id") or "",
        app_id=row.get("app_id") or "",
        owner_wallet_id=row.get("owner_wallet_id") or "",
        status=row.get("status") or "active",
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("", response_model=PrivateDBInfo)
def create_private_db(
    req: PrivateDBCreateRequest,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=req.wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, req.app_id, operator_wallet_id)
        data_wallet_id = normalize_wallet_id(req.data_wallet_id) or operator_wallet_id

        existing = deps.datasource.private_dbs.get_by_owner(app_id=req.app_id, owner_wallet_id=data_wallet_id)
        if existing and not req.private_db_id:
            return _as_info(existing)

        private_db_id = deps.datasource.private_dbs.create(
            app_id=req.app_id,
            owner_wallet_id=data_wallet_id,
            private_db_id=(req.private_db_id or "").strip() or None,
        )
        row = deps.datasource.private_dbs.get(private_db_id)
        if not row:
            raise HTTPException(status_code=500, detail="failed to create private db")
        deps.datasource.audit_logs.create(
            action="private_db.create",
            operator_wallet_id=operator_wallet_id,
            app_id=req.app_id,
            entity_type="private_db",
            entity_id=private_db_id,
            meta={"data_wallet_id": data_wallet_id},
        )
        return _as_info(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=PrivateDBList)
def list_private_dbs(
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    app_id: Optional[str] = None,
    owner_wallet_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps=Depends(get_deps),
):
    operator_wallet = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )
    if session_id and not app_id:
        raise HTTPException(status_code=400, detail="app_id is required when using session_id")

    super_admin = is_super_admin(deps, operator_wallet)
    if not app_id:
        if not super_admin:
            raise HTTPException(status_code=400, detail="app_id is required")
    else:
        try:
            ensure_app_owner(deps, app_id, operator_wallet)
            is_app_owner = True
        except HTTPException:
            is_app_owner = False

        if not is_app_owner and not super_admin:
            if owner_wallet_id and owner_wallet_id != operator_wallet:
                raise HTTPException(status_code=403, detail="owner_wallet_id not accessible")
            owner_wallet_id = operator_wallet

    rows = deps.datasource.private_dbs.list_all(
        owner_wallet_id=(normalize_wallet_id(owner_wallet_id) or None),
        app_id=app_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return PrivateDBList(items=[_as_info(row) for row in rows])


@router.get("/{private_db_id}", response_model=PrivateDBInfo)
def get_private_db(
    private_db_id: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    operator_wallet = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )
    row = deps.datasource.private_dbs.get(private_db_id)
    if not row:
        raise HTTPException(status_code=404, detail="private db not found")
    if normalize_wallet_id(row.get("owner_wallet_id")) != operator_wallet:
        if not is_super_admin(deps, operator_wallet):
            ensure_app_owner(deps, row.get("app_id"), operator_wallet)
    return _as_info(row)


@router.post("/{private_db_id}/bind", response_model=PrivateDBBindResponse)
def bind_private_db(
    private_db_id: str,
    req: PrivateDBBindRequest,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    deps=Depends(get_deps),
):
    try:
        operator_wallet_id = resolve_operator_wallet_id(
            request_wallet_id=req.wallet_id,
            auth_wallet_id=auth_wallet_id,
            allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
        )
        ensure_app_owner(deps, req.app_id, operator_wallet_id)
        data_wallet_id = normalize_wallet_id(req.data_wallet_id) or operator_wallet_id
        deps.datasource.private_dbs.ensure_owner(
            private_db_id=private_db_id,
            app_id=req.app_id,
            owner_wallet_id=data_wallet_id,
        )
        session_ids = [s for s in (req.session_ids or []) if str(s).strip()]
        for session_id in session_ids:
            deps.datasource.private_dbs.bind_session(
                private_db_id=private_db_id,
                app_id=req.app_id,
                owner_wallet_id=data_wallet_id,
                session_id=str(session_id),
            )
        if session_ids:
            deps.datasource.audit_logs.create(
                action="private_db.bind_session",
                operator_wallet_id=operator_wallet_id,
                app_id=req.app_id,
                entity_type="private_db",
                entity_id=private_db_id,
                meta={"data_wallet_id": data_wallet_id, "session_ids": session_ids},
            )
        return PrivateDBBindResponse(
            private_db_id=private_db_id,
            session_ids=session_ids,
            bound_count=len(session_ids),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{private_db_id}/sessions", response_model=PrivateDBSessionList)
def list_private_db_sessions(
    private_db_id: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    app_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    operator_wallet = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )
    if not app_id:
        raise HTTPException(status_code=400, detail="app_id is required")
    row = deps.datasource.private_dbs.get(private_db_id)
    if not row:
        raise HTTPException(status_code=404, detail="private db not found")
    if row.get("app_id") != app_id:
        raise HTTPException(status_code=400, detail="app_id does not match private_db")
    if normalize_wallet_id(row.get("owner_wallet_id")) != operator_wallet:
        if not is_super_admin(deps, operator_wallet):
            ensure_app_owner(deps, app_id, operator_wallet)
    owner_wallet_id = row.get("owner_wallet_id") or ""
    sessions = deps.datasource.private_dbs.list_sessions(
        private_db_id=private_db_id,
        app_id=app_id,
        owner_wallet_id=owner_wallet_id,
    )
    return PrivateDBSessionList(
        private_db_id=private_db_id,
        app_id=app_id,
        owner_wallet_id=owner_wallet_id,
        sessions=[PrivateDBSessionInfo(session_id=s.get("session_id") or "", created_at=s.get("created_at")) for s in sessions],
    )


@router.delete("/{private_db_id}/sessions/{session_id}", response_model=PrivateDBUnbindResponse)
def unbind_private_db_session(
    private_db_id: str,
    session_id: str,
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    app_id: Optional[str] = None,
    deps=Depends(get_deps),
):
    operator_wallet = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )
    if not app_id:
        raise HTTPException(status_code=400, detail="app_id is required")
    row = deps.datasource.private_dbs.get(private_db_id)
    if not row:
        raise HTTPException(status_code=404, detail="private db not found")
    if row.get("app_id") != app_id:
        raise HTTPException(status_code=400, detail="app_id does not match private_db")
    if normalize_wallet_id(row.get("owner_wallet_id")) != operator_wallet:
        if not is_super_admin(deps, operator_wallet):
            ensure_app_owner(deps, app_id, operator_wallet)
    owner_wallet_id = row.get("owner_wallet_id") or ""
    removed = deps.datasource.private_dbs.unbind_session(
        private_db_id=private_db_id,
        app_id=app_id,
        owner_wallet_id=owner_wallet_id,
        session_id=session_id,
    )
    deps.datasource.audit_logs.create(
        action="private_db.unbind_session",
        operator_wallet_id=operator_wallet,
        app_id=app_id,
        entity_type="private_db",
        entity_id=private_db_id,
        meta={"session_id": session_id, "removed_count": removed},
    )
    return PrivateDBUnbindResponse(private_db_id=private_db_id, session_id=session_id, removed_count=removed)
