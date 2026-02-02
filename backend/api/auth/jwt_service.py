# -*- coding: utf-8 -*-

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import jwt

from .envelope import now_ms
from .normalize import normalize_wallet_id


@dataclass
class JwtIssueResult:
    access_token: str
    access_expires_at_ms: int
    refresh_token: str
    refresh_expires_at_ms: int
    refresh_id: str


class JwtAuthService:
    """
    In-memory JWT access token + refresh cookie.

    Notes:
    - refresh token is JWT, but its validity is also checked against refresh_store (server-side revocation).
    - refresh_store is per-process; for multi-worker production use Redis/DB.
    """

    def __init__(
        self,
        *,
        jwt_secret: str,
        access_ttl_ms: int,
        refresh_ttl_ms: int,
        refresh_store: Dict[str, Dict[str, Any]],
    ) -> None:
        self.jwt_secret = jwt_secret
        self.access_ttl_ms = int(access_ttl_ms)
        self.refresh_ttl_ms = int(refresh_ttl_ms)
        self.refresh_store = refresh_store

    def issue_tokens(self, address: str) -> JwtIssueResult:
        address = normalize_wallet_id(address)
        refresh_id = secrets.token_hex(16)
        refresh_expires_at = now_ms() + self.refresh_ttl_ms
        self.refresh_store[refresh_id] = {"address": address, "expiresAt": refresh_expires_at}

        refresh_token = jwt.encode(
            {
                "address": address,
                "typ": "refresh",
                "jti": refresh_id,
                "exp": int(time.time() + self.refresh_ttl_ms / 1000),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        access_token = jwt.encode(
            {
                "address": address,
                "typ": "access",
                "sid": refresh_id,
                "exp": int(time.time() + self.access_ttl_ms / 1000),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        return JwtIssueResult(
            access_token=access_token,
            access_expires_at_ms=now_ms() + self.access_ttl_ms,
            refresh_token=refresh_token,
            refresh_expires_at_ms=refresh_expires_at,
            refresh_id=refresh_id,
        )

    def decode_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except Exception as exc:
            raise ValueError("invalid or expired access token") from exc
        if payload.get("typ") != "access":
            raise ValueError("invalid access token")
        address = normalize_wallet_id(payload.get("address"))
        if not address:
            raise ValueError("invalid access token address")
        return address

    def decode_refresh_token(self, token: str) -> Tuple[str, str]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except Exception as exc:
            raise ValueError("invalid refresh token") from exc
        if payload.get("typ") != "refresh" or not payload.get("jti"):
            raise ValueError("invalid refresh token")
        address = normalize_wallet_id(payload.get("address"))
        if not address:
            raise ValueError("invalid refresh token address")
        return address, str(payload.get("jti"))

    def consume_refresh(self, jti: str, address: str) -> None:
        """
        One-time use refresh token semantics:
        - Check refresh_store has matching record and not expired
        - Consume it (delete)
        """
        jti = str(jti)
        address = normalize_wallet_id(address)
        record = self.refresh_store.get(jti)
        if not record or record.get("address") != address or now_ms() > int(record.get("expiresAt") or 0):
            self.refresh_store.pop(jti, None)
            raise ValueError("refresh token expired")
        self.refresh_store.pop(jti, None)

    def revoke_refresh(self, token: str) -> None:
        try:
            _, jti = self.decode_refresh_token(token)
        except Exception:
            return
        self.refresh_store.pop(jti, None)

