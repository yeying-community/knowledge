# api/routers/owner.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException


def require_wallet_id(wallet_id: Optional[str]) -> str:
    if not wallet_id:
        raise HTTPException(status_code=400, detail="wallet_id is required")
    return wallet_id


def is_super_admin(deps, wallet_id: Optional[str]) -> bool:
    if not wallet_id or not getattr(deps, "settings", None):
        return False
    super_admin_id = (deps.settings.super_admin_wallet_id or "").strip()
    if not super_admin_id:
        return False
    return wallet_id == super_admin_id


def ensure_app_owner(deps, app_id: str, wallet_id: Optional[str]):
    wallet_id = require_wallet_id(wallet_id)
    row = deps.datasource.app_store.get(app_id)
    if not row:
        raise HTTPException(status_code=400, detail=f"app_id={app_id} not registered")
    owner = row.get("owner_wallet_id")
    if owner and owner != wallet_id and not is_super_admin(deps, wallet_id):
        raise HTTPException(status_code=403, detail=f"wallet_id does not own app_id={app_id}")
    return row
