# datasource/connections/minio_connection.py
from typing import Optional
from minio import Minio
from .common import HealthResult


class MinioConnection:
    """
    MinIO 连接层（纯基础设施）：
    - 管理 MinIO 客户端生命周期
    - 提供健康检查
    - 不包含 bucket 名称，不包含业务逻辑
    """
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def health(self, enabled: bool = True) -> HealthResult:
        if not enabled:
            return HealthResult(status="disabled", details="minio disabled")

        try:
            self.client.list_buckets()
            return HealthResult(status="ok", details="list_buckets ok")
        except Exception as e:
            return HealthResult(status="error", details=str(e))
