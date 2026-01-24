# rag/identity/identity_manager.py
# -*- coding: utf-8 -*-

from __future__ import annotations
import hashlib
from typing import Optional
from datasource.sqlstores.app_registry_store import AppRegistryStore
from datasource.sqlstores.private_db_store import PrivateDBStore
from .models import Identity
from .session_store import SessionStore


class IdentityManager:
    """
    Identity 层核心入口：
    - 校验 app 是否存在
    - 生成 memory_key
    - 查询/创建 identity_session 记录
    - 给 pipeline/orchestrator 返回 Identity 对象
    """

    def __init__(
        self,
        session_store: SessionStore,
        app_store: AppRegistryStore,
        private_db_store: Optional[PrivateDBStore] = None,
        super_admin_wallet_id: Optional[str] = None,
    ):
        """
        :param session_store: identity/session_store.py 包装的 store
        :param app_store: 用于动态判断 app 是否已注册
        """
        self.session_store = session_store
        self.app_store = app_store
        self.private_db_store = private_db_store
        self.super_admin_wallet_id = (super_admin_wallet_id or "").strip() or None

    # ---------- app 校验 ----------
    def ensure_app_exists(self, app_id: str, wallet_id: str):
        row = self.app_store.get(app_id)
        if not row or row.get("status") != "active":
            raise ValueError(f"Inactive/Unregistered app_id: {app_id}")
        owner = row.get("owner_wallet_id")
        if owner and owner != wallet_id and wallet_id != self.super_admin_wallet_id:
            raise ValueError(f"wallet_id does not own app_id: {app_id}")

    # ---------- memory_key 生成 ----------
    @staticmethod
    def generate_memory_key(wallet_id: str, app_id: str, session_id: str) -> str:
        raw = f"{wallet_id}:{app_id}:{session_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ---------- 公开入口 ----------
    def resolve_identity(self, wallet_id: str, app_id: str, session_id: str) -> Identity:
        """
        对外暴露的唯一接口：
        - app 校验
        - memory_key 重用 or 创建
        - 返回 Identity 对象（供 pipeline / memory service 使用）
        """
        self.ensure_app_exists(app_id, wallet_id)

        # 查找是否已存在会话
        row = self.session_store.get_by_triplet(wallet_id, app_id, session_id)
        if row:
            memory_key = row["memory_key"]
        else:
            # 创建新的 memory_key
            memory_key = self.generate_memory_key(wallet_id, app_id, session_id)
            self.session_store.upsert(memory_key, wallet_id, app_id, session_id)

        private_db_id = None
        if self.private_db_store:
            private_db_id = self.private_db_store.resolve_or_create(
                app_id=app_id,
                owner_wallet_id=wallet_id,
                session_id=session_id,
            )

        return Identity(
            wallet_id=wallet_id,
            app_id=app_id,
            session_id=session_id,
            memory_key=memory_key,
            private_db_id=private_db_id,
        )
