from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryPushRequest(BaseModel):
    wallet_id: str = Field(..., description="用户钱包 ID")
    app_id: str = Field(..., description="业务插件 ID")
    session_id: str = Field(..., description="业务侧会话 ID")
    filename: str = Field(..., description="业务上传的 session 历史文件名")
    description: Optional[str] = Field(None, description="文件说明（可选）")
    summary_threshold: Optional[int] = Field(None, description="摘要触发阈值（可选，覆盖插件配置）")


class MemoryPushResponse(BaseModel):
    status: str
    messages_written: int
    metas: List[Dict[str, Any]] = Field(default_factory=list)


class MemorySessionItem(BaseModel):
    memory_key: str
    wallet_id: str
    app_id: str
    session_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[str] = None


class MemorySessionList(BaseModel):
    items: List[MemorySessionItem] = Field(default_factory=list)
    total: Optional[int] = None


class MemoryContextItem(BaseModel):
    uid: str
    memory_key: str
    wallet_id: str
    app_id: str
    role: str
    url: str
    description: Optional[str] = None
    content_sha256: Optional[str] = None
    qa_count: Optional[int] = None
    is_summarized: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    content: Optional[str] = None


class MemoryContextList(BaseModel):
    items: List[MemoryContextItem] = Field(default_factory=list)
    total: Optional[int] = None


class MemoryContextUpdateRequest(BaseModel):
    role: Optional[str] = Field(None, description="user|assistant|system 或自定义")
    description: Optional[str] = Field(None, description="记忆条目描述")
