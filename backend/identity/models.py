# rag/identity/models.py
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Optional


@dataclass
class Identity:
    """
    RAG 内部标准的身份对象。
    Pipeline / Orchestrator / MemoryService 都只依赖 Identity，
    不需要再传 wallet_id / app_id / session_id / memory_key 四个字段。
    """
    wallet_id: str
    app_id: str
    session_id: str
    memory_key: str  # 内部唯一主键
    private_db_id: Optional[str] = None

    def to_dict(self):
        return {
            "wallet_id": self.wallet_id,
            "app_id": self.app_id,
            "session_id": self.session_id,
            "memory_key": self.memory_key,
            "private_db_id": self.private_db_id,
        }
