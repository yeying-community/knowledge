# api/deps.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from functools import lru_cache

from datasource.sqlstores.app_registry_store import AppRegistryStore
from settings.config import Settings
from datasource.base import Datasource

from core.embedding.embedding_client import EmbeddingClient
from core.llm.llm_client import LLMClient

from core.memory.memory_manager import MemoryManager
from core.kb.kb_manager import KnowledgeBaseManager
from core.kb.kb_registry import KBRegistry
from core.prompt.prompt_builder import PromptBuilder

from identity.identity_manager import IdentityManager
from identity.session_store import SessionStore

from core.orchestrator.query_orchestrator import QueryOrchestrator
from core.orchestrator.app_registry import AppRegistry
from core.orchestrator.pipeline_registry import PipelineRegistry
from core.runtime.plugin_context import PluginContext
from pathlib import Path

def find_project_root(start: Path) -> Path:
    """
    从 start 开始向上查找项目根目录。
    根目录判定依据（满足其一即可）：
      - pyproject.toml
      - .git
      - plugins 目录
      - config.yaml（按你项目习惯可调整）
    """
    start = start.resolve()
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists():
            return p
        if (p / "plugins").is_dir():
            return p
        if (p / "config.yaml").exists():
            return p
    # 兜底：至少返回 start 的上级，避免 None
    return start.parent


# -------------------------------------------------
# Settings
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# -------------------------------------------------
# Datasource
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_datasource() -> Datasource:
    return Datasource(get_settings())


# -------------------------------------------------
# Core clients（无参数构造）
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient(get_settings())


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())


# -------------------------------------------------
# Registries
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_app_registry() -> AppRegistry:
    project_root = str(find_project_root(Path(__file__).resolve()))
    # print("project_root", project_root)
    return AppRegistry(
        project_root=project_root,
        plugins_dirname="plugins",
    )


@lru_cache(maxsize=1)
def get_pipeline_registry() -> PipelineRegistry:
    return PipelineRegistry()


@lru_cache(maxsize=1)
def get_kb_registry() -> KBRegistry:
    return KBRegistry()


# -------------------------------------------------
# Identity
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    ds = get_datasource()
    return SessionStore(ds.identity_session)


@lru_cache(maxsize=1)
def get_identity_manager() -> IdentityManager:
    ds = get_datasource()
    return IdentityManager(
        session_store=get_session_store(),
        app_store=ds.app_store,
        private_db_store=ds.private_dbs,
        super_admin_wallet_id=get_settings().super_admin_wallet_id,
    )


# -------------------------------------------------
# Core managers（严格按构造函数）
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_memory_manager() -> MemoryManager:
    ds = get_datasource()
    return MemoryManager(
        ds=ds,
        llm=get_llm_client(),
        embedder=get_embedding_client(),
    )


@lru_cache(maxsize=1)
def get_kb_manager() -> KnowledgeBaseManager:
    ds = get_datasource()
    return KnowledgeBaseManager(
        ds=ds,
        embedding_client=get_embedding_client(),
        kb_registry=get_kb_registry(),
    )


@lru_cache(maxsize=1)
def get_prompt_builder() -> PromptBuilder:
    project_root = str(find_project_root(Path(__file__).resolve()))
    return PromptBuilder(project_root=project_root)


# -------------------------------------------------
# Orchestrator
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_orchestrator() -> QueryOrchestrator:
    ds = get_datasource()
    return QueryOrchestrator(
        identity_manager=get_identity_manager(),
        app_registry=get_app_registry(),
        app_store=ds.app_store,
        memory_manager=get_memory_manager(),
        kb_manager=get_kb_manager(),
        prompt_builder=get_prompt_builder(),
        llm_client=get_llm_client(),
    )

# api/deps.py
from dataclasses import dataclass


@dataclass
class Deps:
    settings: Settings
    datasource: Datasource

    app_registry: AppRegistry
    pipeline_registry: PipelineRegistry
    kb_registry: KBRegistry

    identity_manager: IdentityManager
    session_store: SessionStore

    memory_manager: MemoryManager
    kb_manager: KnowledgeBaseManager
    prompt_builder: PromptBuilder

    llm_client: LLMClient
    embedding_client: EmbeddingClient

    orchestrator: QueryOrchestrator


# -------------------------------------------------
# Deps (API 层统一依赖)
# -------------------------------------------------
@lru_cache(maxsize=1)
def get_deps() -> Deps:
    settings = get_settings()
    datasource = get_datasource()

    app_registry = get_app_registry()
    pipeline_registry = get_pipeline_registry()
    kb_registry = get_kb_registry()

    session_store = get_session_store()
    identity_manager = get_identity_manager()

    embedding_client = get_embedding_client()
    llm_client = get_llm_client()

    memory_manager = get_memory_manager()
    kb_manager = get_kb_manager()
    prompt_builder = get_prompt_builder()

    orchestrator = get_orchestrator()
    plugin_context = PluginContext(
        settings=settings,
        datasource=datasource,
        app_registry=app_registry,
        orchestrator=orchestrator,
    )
    pipeline_registry.configure(app_registry, orchestrator, plugin_context)

    return Deps(
        settings=settings,
        datasource=datasource,

        app_registry=app_registry,
        pipeline_registry=pipeline_registry,
        kb_registry=kb_registry,

        identity_manager=identity_manager,
        session_store=session_store,

        memory_manager=memory_manager,
        kb_manager=kb_manager,
        prompt_builder=prompt_builder,

        llm_client=llm_client,
        embedding_client=embedding_client,

        orchestrator=orchestrator,
    )
