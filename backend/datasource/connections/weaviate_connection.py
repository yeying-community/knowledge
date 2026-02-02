# rag/datasource/connections/weaviate_connection.py
from typing import Optional, Dict
import weaviate
from weaviate import connect_to_custom, WeaviateClient
from weaviate.classes.init import Auth
from .common import HealthResult


class WeaviateConnection:
    """
    纯连接层：不负责任何业务逻辑，不负责 schema。
    """

    def __init__(
        self,
        scheme: str,
        host: str,
        port: int,
        grpc_port: int,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.scheme = scheme
        self.host = host
        self.port = int(port)
        self.grpc_port = int(grpc_port)
        self.secure = (scheme.lower() == "https")
        self.api_key = api_key
        self.extra_headers = extra_headers or {}
        self._client: Optional[WeaviateClient] = None

    @property
    def client(self) -> WeaviateClient:
        if self._client is None:
            auth = Auth.api_key(self.api_key) if self.api_key else None
            self._client = connect_to_custom(
                http_host=self.host,
                http_port=self.port,
                http_secure=self.secure,
                grpc_host=self.host,
                grpc_port=self.grpc_port,
                grpc_secure=self.secure,
                auth_credentials=auth,
                headers=self.extra_headers or None,
                skip_init_checks=True,
            )
        return self._client

    def health(self, enabled: bool) -> HealthResult:
        if not enabled:
            return HealthResult(status="disabled", details="WEAVIATE_ENABLED=false")
        try:
            ok = self.client.is_ready()
            if ok:
                return HealthResult(status="ok", details="client.is_ready ok")
            return HealthResult(status="error", details="client.is_ready returned False")
        except Exception as e:
            return HealthResult(status="error", details=str(e))

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except:
                pass
            self._client = None

    def __del__(self):
        self.close()
