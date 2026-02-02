# -*- coding: utf-8 -*-

from __future__ import annotations


def normalize_wallet_id(wallet_id: str | None) -> str:
    """
    Normalize wallet id for comparisons/storage.

    - For EVM addresses: lowercasing is enough for equality checks (we don't checksum here).
    - Keep non-EVM identifiers working (e.g. legacy "super_admin") by not validating format.
    """
    return (wallet_id or "").strip().lower()

