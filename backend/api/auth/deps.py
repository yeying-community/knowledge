# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException

from api.deps import get_deps
from api.auth.jwt_service import JwtAuthService
from api.auth.normalize import normalize_wallet_id
from api.auth.ucan import is_ucan_token, verify_ucan_invocation


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = (parts[1] or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return token


def get_optional_auth_wallet_id(
    authorization: Optional[str] = Header(None),
    deps=Depends(get_deps),
) -> Optional[str]:
    """
    Return authenticated operator wallet id (lowercased) if Authorization is present.
    Supports:
    - SIWE(JWT access token)
    - UCAN invocation token
    """
    token = _parse_bearer(authorization)
    if not token:
        return None

    # 1) UCAN
    if is_ucan_token(token):
        try:
            caps = [{"resource": deps.settings.ucan_resource, "action": deps.settings.ucan_action}]
            return verify_ucan_invocation(
                token,
                audience=deps.settings.ucan_aud,
                required_caps=caps,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    # 2) JWT access token
    try:
        jwt_svc = JwtAuthService(
            jwt_secret=deps.settings.jwt_secret,
            access_ttl_ms=deps.settings.access_ttl_ms,
            refresh_ttl_ms=deps.settings.refresh_ttl_ms,
            refresh_store={},  # not needed for access token verification
        )
        return jwt_svc.decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_auth_wallet_id(
    auth_wallet_id: Optional[str] = Depends(get_optional_auth_wallet_id),
) -> str:
    if not auth_wallet_id:
        raise HTTPException(status_code=401, detail="Missing access token")
    return auth_wallet_id


def resolve_operator_wallet_id(
    *,
    request_wallet_id: Optional[str],
    auth_wallet_id: Optional[str],
    allow_insecure: bool,
) -> str:
    """
    Resolve operator wallet id with backward-compatible request parameter/body support.

    Security:
    - If Authorization is present, request_wallet_id (if provided) must match it.
    - If Authorization is missing, request_wallet_id is only accepted when allow_insecure=True.
    """
    req = normalize_wallet_id(request_wallet_id)
    auth = normalize_wallet_id(auth_wallet_id)

    if auth:
        if req and req != auth:
            raise HTTPException(status_code=401, detail="wallet_id does not match access token")
        return auth

    if req and allow_insecure:
        return req

    raise HTTPException(status_code=401, detail="Missing access token")

