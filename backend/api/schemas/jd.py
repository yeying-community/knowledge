from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class JDUploadRequest(BaseModel):
    wallet_id: str = Field(..., description="操作钱包 ID")
    app_id: Optional[str] = Field(None, description="可选：业务插件 ID（未传则使用路径参数）")
    jd: Any = Field(..., description="JD JSON 或文本")
    session_id: Optional[str] = Field(None, description="可选：业务会话 ID")
    private_db_id: Optional[str] = Field(None, description="可选：私有库 ID（与 session_id 二选一）")
    jd_id: Optional[str] = Field(None, description="可选：业务侧 JD ID")
    kb_key: Optional[str] = Field(None, description="可选：指定 user_upload KB")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选：补充元数据")


class JDUploadResponse(BaseModel):
    jd_id: str
    kb_key: str
    collection: str
    doc_id: str
    source_url: str
