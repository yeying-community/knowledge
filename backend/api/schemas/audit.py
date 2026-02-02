# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLogItem(BaseModel):
    id: int
    operator_wallet_id: Optional[str] = None
    app_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class AuditLogList(BaseModel):
    items: List[AuditLogItem] = Field(default_factory=list)
