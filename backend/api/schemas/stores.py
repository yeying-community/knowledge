from typing import List, Optional

from pydantic import BaseModel, Field


class StoreHealthItem(BaseModel):
    name: str = Field(..., description="Store name")
    status: str = Field(..., description="ok|error|disabled|configured")
    details: Optional[str] = Field(None, description="Health detail message")


class StoresHealthResponse(BaseModel):
    stores: List[StoreHealthItem]
