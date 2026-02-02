from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KBInfo(BaseModel):
    app_id: str = Field(..., description="Plugin app_id")
    kb_key: str = Field(..., description="Logical KB key in config")
    kb_type: str = Field(..., description="KB type")
    collection: str = Field(..., description="Vector collection name")
    text_field: str = Field("text", description="Text field name in properties")
    top_k: int = Field(..., description="Top-k retrieval size")
    weight: float = Field(..., description="Score weight")
    use_allowed_apps_filter: bool = Field(False, description="Filter by allowed apps")
    vector_fields: List[str] = Field(default_factory=list, description="Fields used for embedding")
    schema: List[Dict[str, Any]] = Field(default_factory=list, description="Schema field configs")
    status: Optional[str] = Field(None, description="App status in registry")


class KBStats(BaseModel):
    app_id: str
    kb_key: str
    collection: str
    total_count: int
    chunk_count: int


class KBDocument(BaseModel):
    id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KBDocumentList(BaseModel):
    items: List[KBDocument] = Field(default_factory=list)
    total: Optional[int] = None


class KBDocumentUpsert(BaseModel):
    id: Optional[str] = Field(None, description="Optional object ID")
    text: Optional[str] = Field(None, description="Text content for embedding")
    properties: Dict[str, Any] = Field(default_factory=dict)
    vector: Optional[List[float]] = None


class KBDocumentUpdate(BaseModel):
    text: Optional[str] = Field(None, description="Text content for embedding")
    properties: Dict[str, Any] = Field(default_factory=dict)
    vector: Optional[List[float]] = None


class KBConfigInfo(BaseModel):
    app_id: str = Field(..., description="Plugin app_id")
    kb_key: str = Field(..., description="Logical KB key in config")
    kb_type: str = Field(..., description="KB type")
    collection: str = Field(..., description="Vector collection name")
    text_field: str = Field("text", description="Text field name in properties")
    top_k: int = Field(..., description="Top-k retrieval size")
    weight: float = Field(..., description="Score weight")
    use_allowed_apps_filter: bool = Field(False, description="Filter by allowed apps")
    vector_fields: List[str] = Field(default_factory=list, description="Fields used for embedding")
    schema: List[Dict[str, Any]] = Field(default_factory=list, description="Schema field configs")


class KBConfigCreate(BaseModel):
    kb_key: str = Field(..., description="Logical KB key in config")
    kb_type: str = Field(..., description="KB type")
    collection: str = Field(..., description="Vector collection name")
    text_field: str = Field("text", description="Text field name in properties")
    top_k: int = Field(3, description="Top-k retrieval size")
    weight: float = Field(1.0, description="Score weight")
    use_allowed_apps_filter: bool = Field(False, description="Filter by allowed apps")
    vector_fields: List[str] = Field(default_factory=list, description="Fields used for embedding")
    schema: List[Dict[str, Any]] = Field(default_factory=list, description="Schema field configs")


class KBConfigUpdate(BaseModel):
    kb_type: Optional[str] = Field(None, description="KB type")
    collection: Optional[str] = Field(None, description="Vector collection name")
    text_field: Optional[str] = Field(None, description="Text field name in properties")
    top_k: Optional[int] = Field(None, description="Top-k retrieval size")
    weight: Optional[float] = Field(None, description="Score weight")
    use_allowed_apps_filter: Optional[bool] = Field(None, description="Filter by allowed apps")
    vector_fields: Optional[List[str]] = Field(None, description="Fields used for embedding")
    schema: Optional[List[Dict[str, Any]]] = Field(None, description="Schema field configs")
