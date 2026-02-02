# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.auth.deps import get_optional_auth_wallet_id, resolve_operator_wallet_id
from api.routers.owner import ensure_app_owner, is_super_admin
from api.schemas.audit import AuditLogItem, AuditLogList

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogList)
def list_audit_logs(
    wallet_id: Optional[str] = None,
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
    app_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    operator_wallet_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    deps=Depends(get_deps),
):
    operator_wallet = resolve_operator_wallet_id(
        request_wallet_id=wallet_id,
        auth_wallet_id=auth_wallet_id,
        allow_insecure=deps.settings.auth_allow_insecure_wallet_id,
    )

    super_admin = is_super_admin(deps, operator_wallet)
    if not app_id:
        if not super_admin:
            raise HTTPException(status_code=400, detail="app_id is required")
    else:
        try:
            ensure_app_owner(deps, app_id, operator_wallet)
            is_owner = True
        except HTTPException:
            is_owner = False
        if not super_admin and not is_owner:
            raise HTTPException(status_code=403, detail="wallet_id cannot access audit logs")

    rows = deps.datasource.audit_logs.list(
        limit=limit,
        offset=offset,
        app_id=app_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        operator_wallet_id=operator_wallet_id,
    )

    items = []
    for row in rows:
        meta = {}
        raw = row.get("meta_json")
        if raw:
            try:
                meta = json.loads(raw)
            except Exception:
                meta = {}
        items.append(
            AuditLogItem(
                id=row.get("id"),
                operator_wallet_id=row.get("operator_wallet_id"),
                app_id=row.get("app_id"),
                entity_type=row.get("entity_type"),
                entity_id=row.get("entity_id"),
                action=row.get("action") or "",
                meta=meta,
                created_at=row.get("created_at"),
            )
        )

    return AuditLogList(items=items)
