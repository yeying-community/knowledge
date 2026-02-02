# datasource/objectstores/minio_store.py
from __future__ import annotations
import io, json
from typing import Optional, List
from minio.error import S3Error
from ..connections.minio_connection import MinioConnection


class MinIOStore:
    """
    MinIOStore（纯 infra 层）：
    - 不管理 bucket 名称
    - 不创建 bucket（由上层决定）
    - 不提供 make_key（由上层决定）
    - 提供最纯粹的存储 API
    """

    def __init__(self, conn: MinioConnection):
        self.conn = conn

    @property
    def client(self):
        return self.conn.client

    # -------- Bucket 基本操作（无自动创建） --------
    def bucket_exists(self, bucket: str) -> bool:
        return self.client.bucket_exists(bucket)

    def create_bucket(self, bucket: str) -> None:
        if not self.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def delete_bucket(self, bucket: str) -> None:
        for obj in self.client.list_objects(bucket, recursive=True):
            self.client.remove_object(bucket, obj.object_name)
        self.client.remove_bucket(bucket)

    # -------- Object API --------
    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        self.client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)
        return key

    def get_bytes(self, bucket: str, key: str) -> bytes:
        resp = self.client.get_object(bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def delete(self, bucket: str, key: str) -> None:
        self.client.remove_object(bucket, key)

    def list(self, bucket: str, prefix: str = "", recursive=True) -> List[str]:
        return [o.object_name for o in self.client.list_objects(bucket, prefix, recursive)]

    # -------- Text / JSON API（轻量方便） --------
    def put_text(self, bucket: str, key: str, text: str, encoding="utf-8") -> str:
        return self.put_bytes(bucket, key, text.encode(encoding), "text/plain")

    def get_text(self, bucket: str, key: str, encoding="utf-8") -> str:
        return self.get_bytes(bucket, key).decode(encoding)

    def put_json(self, bucket: str, key: str, obj) -> str:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        return self.put_bytes(bucket, key, data, "application/json")

    def get_json(self, bucket: str, key: str):
        text = self.get_text(bucket, key)
        return json.loads(text)
