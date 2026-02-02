# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_deps
from api.auth.deps import require_auth_wallet_id
from api.auth.envelope import now_ms, ok
from api.routers.owner import is_super_admin

router = APIRouter(prefix="/api/v1/public", tags=["public"])


@router.get("/profile")
def public_profile(
    wallet_id: str = Depends(require_auth_wallet_id),
    deps=Depends(get_deps),
):
    return ok(
        {
            "address": wallet_id,
            "is_super_admin": is_super_admin(deps, wallet_id),
            "issuedAt": now_ms(),
        }
    )
