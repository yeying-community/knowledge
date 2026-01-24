from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ResumeUploadRequest(BaseModel):
    wallet_id: str = Field(..., description="操作钱包 ID")
    app_id: str = Field(..., description="业务插件 ID")
    resume: Any = Field(..., description="简历 JSON 或文本")
    session_id: Optional[str] = Field(None, description="可选：业务会话 ID")
    private_db_id: Optional[str] = Field(None, description="可选：私有库 ID（与 session_id 二选一）")
    resume_id: Optional[str] = Field(None, description="可选：业务侧简历 ID")
    kb_key: Optional[str] = Field(None, description="可选：指定 user_upload KB")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选：补充元数据")


class ResumeUploadResponse(BaseModel):
    resume_id: str
    kb_key: str
    collection: str
    doc_id: str
    source_url: str
