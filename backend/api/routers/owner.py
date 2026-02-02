# api/routers/owner.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from api.auth.normalize import normalize_wallet_id


def require_wallet_id(wallet_id: Optional[str]) -> str:
    wallet_id = normalize_wallet_id(wallet_id)
    if not wallet_id:
        raise HTTPException(status_code=400, detail="wallet_id is required")
    return wallet_id


def is_super_admin(deps, wallet_id: Optional[str]) -> bool:
    wallet_id = normalize_wallet_id(wallet_id)
    if not wallet_id or not getattr(deps, "settings", None):
        return False
    super_admin_id = normalize_wallet_id(deps.settings.super_admin_wallet_id)
    if not super_admin_id:
        return False
    return wallet_id == super_admin_id


def ensure_app_owner(deps, app_id: str, wallet_id: Optional[str]):
    wallet_id = require_wallet_id(wallet_id)
    row = deps.datasource.app_store.get(app_id)
    if not row:
        raise HTTPException(status_code=400, detail=f"app_id={app_id} not registered")
    owner = normalize_wallet_id(row.get("owner_wallet_id"))
    if owner and owner != wallet_id and not is_super_admin(deps, wallet_id):
        raise HTTPException(status_code=403, detail=f"wallet_id does not own app_id={app_id}")
    return row


def ensure_can_act_for_data_wallet(
    deps,
    *,
    app_id: str,
    operator_wallet_id: Optional[str],
    data_wallet_id: Optional[str],
) -> None:
    """
    Authorization rule for "operate on user private data":
    - A user can operate on their own data: operator_wallet_id == data_wallet_id
    - Otherwise, only the app owner (tenant) or super admin can act on behalf of data_wallet_id.
    """
    operator_wallet_id = require_wallet_id(operator_wallet_id)
    data_wallet_id = normalize_wallet_id(data_wallet_id)
    if not data_wallet_id:
        raise HTTPException(status_code=400, detail="data_wallet_id is required")

    if operator_wallet_id == data_wallet_id:
        return
    if is_super_admin(deps, operator_wallet_id):
        return

    row = deps.datasource.app_store.get(app_id)
    if not row:
        raise HTTPException(status_code=400, detail=f"app_id={app_id} not registered")
    owner = normalize_wallet_id(row.get("owner_wallet_id"))
    if owner and owner == operator_wallet_id:
        return
    raise HTTPException(status_code=403, detail="wallet_id cannot operate on data_wallet_id")
