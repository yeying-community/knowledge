from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestionLogCreate(BaseModel):
    wallet_id: str = Field(..., description="开发者钱包 ID（权限校验）")
    status: str = Field(..., description="started|success|failed|info")
    message: Optional[str] = Field("", description="Log message")
    app_id: str = Field(..., description="Plugin app_id")
    kb_key: Optional[str] = Field(None, description="KB key")
    collection: Optional[str] = Field(None, description="Vector collection")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class IngestionLogItem(BaseModel):
    id: int
    status: str
    message: Optional[str] = None
    wallet_id: Optional[str] = None
    app_id: Optional[str] = None
    kb_key: Optional[str] = None
    collection: Optional[str] = None
    meta_json: Optional[str] = None
    created_at: Optional[str] = None


class IngestionLogList(BaseModel):
    items: List[IngestionLogItem] = Field(default_factory=list)
