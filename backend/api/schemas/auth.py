# -*- coding: utf-8 -*-

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthChallengeRequest(BaseModel):
    address: str = Field(..., description="EVM address (0x...)")


class AuthVerifyRequest(BaseModel):
    address: str = Field(..., description="EVM address (0x...)")
    signature: str = Field(..., description="Signature for the issued challenge (personal_sign)")

