from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    wallet_id: Optional[str] = Field(None, description="操作钱包 ID（兼容字段；推荐使用 Authorization）")
    data_wallet_id: Optional[str] = Field(
        None,
        description="可选：数据归属钱包 ID（业务用户）。默认等于 wallet_id。",
    )
    app_id: str = Field(..., description="业务插件 ID")
    session_id: str = Field(..., description="业务侧会话 ID")
    intent: str = Field(..., description="业务意图，如 generate_questions")
    query: Optional[str] = Field(None, description="用户输入（未提供简历时的兜底）")
    resume_id: Optional[str] = Field(None, description="可选：中台返回的简历 ID")
    jd_id: Optional[str] = Field(None, description="可选：中台返回的 JD ID")
    target: Optional[str] = Field(None, description="可选：目标岗位")
    company: Optional[str] = Field(None, description="可选：公司名")
    intent_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: dict
