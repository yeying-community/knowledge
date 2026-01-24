# settings/config.py
from pydantic import BaseModel
import os
from pathlib import Path
from dotenv import load_dotenv

# ===== 只加载一次 .env =====
def _load_env() -> None:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        env_path = p / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
            return
    load_dotenv(override=True)


_load_env()


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


def _env_int(key: str, default: int = 0) -> int:
    raw = os.getenv(key, "")
    try:
        return int(raw)
    except Exception:
        return default

class Settings(BaseModel):
    # ---------- MinIO ----------
    minio_enabled: bool = _env_bool("MINIO_ENABLED", "true")
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_secure: bool = _env_bool("MINIO_SECURE", "false")

    # ⭐ 唯一 bucket（与你的 .env 对齐）
    minio_bucket: str = os.getenv("MINIO_BUCKET_KB", "rag")

    # ---------- SQLite ----------
    sqlite_path: str = os.getenv(
        "SQLITE_PATH",
        str((Path(__file__).resolve().parents[1] / "data" / "rag.sqlite3")),
    )

    # ---------- Weaviate ----------
    weaviate_api_key: str = os.getenv("WEAVIATE_API_KEY", "")
    # Weaviate
    weaviate_enabled: bool = _env_bool("WEAVIATE_ENABLED", "false")
    weaviate_scheme: str = os.getenv("WEAVIATE_SCHEME", "http")
    weaviate_host: str = os.getenv("WEAVIATE_HOST", "47.101.3.196")
    weaviate_port: int = _env_int("WEAVIATE_PORT", 8080)
    weaviate_grpc_port: int = _env_int("WEAVIATE_GRPC_PORT", 50051)


    # ---------- OpenAI ----------
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "")

    embed_model: str = os.getenv("EMBED_MODEL", "")
    embed_api_key: str = os.getenv("EMBED_API_KEY", "")
    embed_api_base: str = os.getenv("EMBED_API_BASE", "")
    embed_dim: int = _env_int("EMBEDDING_DIM", 0)
    # ---------- Plugins ----------
    plugins_auto_register: str = os.getenv("PLUGINS_AUTO_REGISTER", "interviewer")

    # ---------- Access Control ----------
    super_admin_wallet_id: str = os.getenv("SUPER_ADMIN_WALLET_ID", "super_admin")
