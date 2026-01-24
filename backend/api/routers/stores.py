# api/routers/stores.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends

from api.deps import get_deps
from api.schemas.stores import StoresHealthResponse, StoreHealthItem

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/health", response_model=StoresHealthResponse)
def stores_health(deps=Depends(get_deps)):
    stores = []

    # SQLite
    try:
        deps.datasource.sqlite_conn.query_one("SELECT 1")
        stores.append(StoreHealthItem(name="sqlite", status="ok", details="SELECT 1 ok"))
    except Exception as e:
        stores.append(StoreHealthItem(name="sqlite", status="error", details=str(e)))

    # MinIO
    if deps.datasource.minio_conn:
        res = deps.datasource.minio_conn.health(enabled=True)
        stores.append(StoreHealthItem(name="minio", status=res.status, details=res.details))
    else:
        stores.append(StoreHealthItem(name="minio", status="disabled", details="minio disabled"))

    # Weaviate
    if deps.datasource.weaviate_conn:
        res = deps.datasource.weaviate_conn.health(enabled=True)
        stores.append(StoreHealthItem(name="weaviate", status=res.status, details=res.details))
    else:
        stores.append(StoreHealthItem(name="weaviate", status="disabled", details="weaviate disabled"))

    # LLM
    settings = deps.settings
    if settings.openai_api_key and (settings.openai_model or settings.openai_api_base):
        stores.append(StoreHealthItem(name="llm", status="configured", details="openai configured"))
    elif settings.openai_api_key:
        stores.append(StoreHealthItem(name="llm", status="configured", details="openai api key set"))
    else:
        stores.append(StoreHealthItem(name="llm", status="disabled", details="OPENAI_API_KEY missing"))

    return StoresHealthResponse(stores=stores)
