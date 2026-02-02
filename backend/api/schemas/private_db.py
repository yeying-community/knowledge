# -*- coding: utf-8 -*-

from typing import List, Optional

from pydantic import BaseModel, Field


class PrivateDBCreateRequest(BaseModel):
    wallet_id: Optional[str] = Field(None, description="操作钱包 ID（兼容字段；推荐使用 Authorization）")
    app_id: str = Field(..., description="业务插件 ID")
    data_wallet_id: Optional[str] = Field(
        None,
        description="可选：数据归属钱包 ID（业务用户）。默认等于 wallet_id。",
    )
    private_db_id: Optional[str] = Field(None, description="可选：自定义私有库 ID")


class PrivateDBBindRequest(BaseModel):
    wallet_id: Optional[str] = Field(None, description="操作钱包 ID（兼容字段；推荐使用 Authorization）")
    app_id: str = Field(..., description="业务插件 ID")
    data_wallet_id: Optional[str] = Field(
        None,
        description="可选：数据归属钱包 ID（业务用户）。默认等于 wallet_id。",
    )
    session_ids: List[str] = Field(..., description="绑定的 session_id 列表")


class PrivateDBInfo(BaseModel):
    private_db_id: str
    app_id: str
    owner_wallet_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PrivateDBList(BaseModel):
    items: List[PrivateDBInfo] = Field(default_factory=list)


class PrivateDBBindResponse(BaseModel):
    private_db_id: str
    session_ids: List[str]
    bound_count: int


class PrivateDBSessionInfo(BaseModel):
    session_id: str
    created_at: Optional[str] = None


class PrivateDBSessionList(BaseModel):
    private_db_id: str
    app_id: str
    owner_wallet_id: str
    sessions: List[PrivateDBSessionInfo] = Field(default_factory=list)


class PrivateDBUnbindResponse(BaseModel):
    private_db_id: str
    session_id: str
    removed_count: int
