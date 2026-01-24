# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class IngestionJobCreate(BaseModel):
    wallet_id: str = Field(..., description="开发者钱包 ID")
    data_wallet_id: Optional[str] = Field(None, description="数据归属钱包 ID（业务用户）")
    private_db_id: Optional[str] = Field(None, description="私有库 ID（session_id 二选一）")
    session_id: Optional[str] = Field(None, description="业务会话 ID（私有库绑定）")
    app_id: str = Field(..., description="Plugin app_id")
    kb_key: str = Field(..., description="KB key")
    source_url: Optional[str] = Field(None, description="MinIO URL (minio://bucket/key)")
    content: Optional[str] = Field(None, description="Inline text content (will be stored to MinIO)")
    filename: Optional[str] = Field(None, description="Optional filename for inline content")
    file_type: Optional[str] = Field(None, description="Optional file type override")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    options: Dict[str, Any] = Field(default_factory=dict, description="Job options")

    @model_validator(mode="after")
    def validate_source(self) -> "IngestionJobCreate":
        if not self.source_url and not self.content:
            raise ValueError("source_url or content is required")
        return self


class IngestionJobInfo(BaseModel):
    id: int
    wallet_id: str
    data_wallet_id: Optional[str] = None
    private_db_id: Optional[str] = None
    app_id: str
    kb_key: str
    job_type: str
    source_url: Optional[str] = None
    file_type: Optional[str] = None
    status: str
    options_json: Optional[str] = None
    result_json: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class IngestionJobRunItem(BaseModel):
    id: int
    job_id: int
    status: str
    message: Optional[str] = None
    meta_json: Optional[str] = None
    created_at: Optional[str] = None


class IngestionJobList(BaseModel):
    items: List[IngestionJobInfo] = Field(default_factory=list)


class IngestionJobRuns(BaseModel):
    items: List[IngestionJobRunItem] = Field(default_factory=list)


class IngestionJobPreset(BaseModel):
    bucket: str
    prefix: str
    recent_keys: List[str] = Field(default_factory=list)
