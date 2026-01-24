# rag/identity/session_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Optional
from datasource.sqlstores.identity_session_store import IdentitySessionStore


class SessionStore:
    """
    Identity 层的 session store，只暴露 Identity 层需要的方法。
    内部封装 datasource/sqlstores.identity_session_store
    """

    def __init__(self, underlying: IdentitySessionStore):
        self.underlying = underlying

    def get_by_triplet(self, wallet_id: str, app_id: str, session_id: str):
        """根据三元组查找 memory_key"""
        return self.underlying.get(wallet_id, app_id, session_id)

    def get_by_memory_key(self, memory_key: str):
        return self.underlying.get_by_memory_key(memory_key)

    def upsert(self, memory_key: str, wallet_id: str, app_id: str, session_id: str):
        self.underlying.upsert(memory_key, wallet_id, app_id, session_id)
