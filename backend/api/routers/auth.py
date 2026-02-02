# -*- coding: utf-8 -*-

from __future__ import annotations

import secrets
from typing import Dict

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from api.auth.envelope import fail, now_ms, ok
from api.auth.jwt_service import JwtAuthService
from api.auth.normalize import normalize_wallet_id
from api.deps import get_deps
from api.schemas.auth import AuthChallengeRequest, AuthVerifyRequest

router = APIRouter(prefix="/api/v1/public/auth", tags=["auth"])

# In-memory stores (dev/demo). Replace with Redis/DB in production.
_challenges: Dict[str, dict] = {}
_refresh_store: Dict[str, dict] = {}


def _jwt_svc(deps) -> JwtAuthService:
    return JwtAuthService(
        jwt_secret=deps.settings.jwt_secret,
        access_ttl_ms=deps.settings.access_ttl_ms,
        refresh_ttl_ms=deps.settings.refresh_ttl_ms,
        refresh_store=_refresh_store,
    )


def _set_refresh_cookie(deps, response: JSONResponse, token: str, max_age: int) -> None:
    response.set_cookie(
        "refresh_token",
        token,
        max_age=max(int(max_age), 1),
        httponly=True,
        secure=bool(deps.settings.cookie_secure),
        samesite=str(deps.settings.cookie_samesite or "lax").lower(),
        path="/api/v1/public/auth",
    )


def _clear_refresh_cookie(deps, response: JSONResponse) -> None:
    response.set_cookie(
        "refresh_token",
        "",
        max_age=0,
        httponly=True,
        secure=bool(deps.settings.cookie_secure),
        samesite=str(deps.settings.cookie_samesite or "lax").lower(),
        path="/api/v1/public/auth",
    )


@router.post("/challenge")
def auth_challenge(req: AuthChallengeRequest, deps=Depends(get_deps)):
    address = normalize_wallet_id(req.address)
    if not address:
        raise HTTPException(status_code=400, detail=fail(400, "Missing address"))

    nonce = secrets.token_hex(8)
    issued_at = now_ms()
    expires_at = issued_at + 5 * 60 * 1000
    challenge_text = f"Sign to login\n\nnonce: {nonce}\nissuedAt: {issued_at}"

    _challenges[address] = {
        "challenge": challenge_text,
        "issuedAt": issued_at,
        "expiresAt": expires_at,
    }

    return ok(
        {
            "address": address,
            "challenge": challenge_text,
            "nonce": nonce,
            "issuedAt": issued_at,
            "expiresAt": expires_at,
        }
    )


@router.post("/verify")
def auth_verify(req: AuthVerifyRequest, deps=Depends(get_deps)):
    address = normalize_wallet_id(req.address)
    signature = (req.signature or "").strip()
    if not address or not signature:
        raise HTTPException(status_code=400, detail=fail(400, "Missing address or signature"))

    record = _challenges.get(address)
    if not record or now_ms() > int(record.get("expiresAt") or 0):
        _challenges.pop(address, None)
        raise HTTPException(status_code=400, detail=fail(400, "Challenge expired"))

    try:
        message = encode_defunct(text=record["challenge"])
        recovered = Account.recover_message(message, signature=signature)
        if normalize_wallet_id(recovered) != address:
            raise HTTPException(status_code=401, detail=fail(401, "Invalid signature"))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail=fail(401, "Invalid signature"))
    finally:
        _challenges.pop(address, None)

    issued = _jwt_svc(deps).issue_tokens(address)
    resp = JSONResponse(
        ok(
            {
                "address": address,
                "token": issued.access_token,
                "expiresAt": issued.access_expires_at_ms,
                "refreshExpiresAt": issued.refresh_expires_at_ms,
            }
        )
    )
    _set_refresh_cookie(deps, resp, issued.refresh_token, int(deps.settings.refresh_ttl_ms / 1000))
    return resp


@router.post("/refresh")
def auth_refresh(request: Request, deps=Depends(get_deps)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail=fail(401, "Missing refresh token"))

    jwt_svc = _jwt_svc(deps)
    try:
        address, jti = jwt_svc.decode_refresh_token(refresh_token)
    except Exception:
        resp = JSONResponse(fail(401, "Invalid refresh token"), status_code=401)
        _clear_refresh_cookie(deps, resp)
        return resp

    try:
        jwt_svc.consume_refresh(jti, address)
    except Exception:
        resp = JSONResponse(fail(401, "Refresh token expired"), status_code=401)
        _clear_refresh_cookie(deps, resp)
        return resp

    issued = jwt_svc.issue_tokens(address)
    resp = JSONResponse(
        ok(
            {
                "address": address,
                "token": issued.access_token,
                "expiresAt": issued.access_expires_at_ms,
                "refreshExpiresAt": issued.refresh_expires_at_ms,
            }
        )
    )
    _set_refresh_cookie(deps, resp, issued.refresh_token, int(deps.settings.refresh_ttl_ms / 1000))
    return resp


@router.post("/logout")
def auth_logout(request: Request, deps=Depends(get_deps)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            _jwt_svc(deps).revoke_refresh(refresh_token)
        except Exception:
            pass

    resp = JSONResponse(ok({"logout": True}))
    _clear_refresh_cookie(deps, resp)
    return resp

