import io
import json
import mimetypes
import os
import re
import uuid
from abc import ABC, abstractmethod

from . import config
from .errors import ServiceUnavailableError


class StorageClient(ABC):
    @abstractmethod
    def save(self, folder: str, file_name: str, content: bytes) -> str:
        pass


class MinioStorage(StorageClient):
    def __init__(self, client=None):
        if client is None:
            from minio import Minio
            client = Minio(config.MINIO_ENDPOINT, access_key=config.MINIO_ACCESS_KEY,
                           secret_key=config.MINIO_SECRET_KEY, secure=config.MINIO_SECURE)
        self._client, self._bucket, self._ready = client, config.MINIO_BUCKET, False

    def _ensure_bucket(self) -> None:
        if self._ready:
            return
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"AWS": ["*"]},
                  "Action": ["s3:GetObject"], "Resource": [f"arn:aws:s3:::{self._bucket}/*"]}]}
        self._client.set_bucket_policy(self._bucket, json.dumps(policy))
        self._ready = True

    def save(self, folder: str, file_name: str, content: bytes) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(file_name or "file"))
        key = f"{folder}/{uuid.uuid4().hex[:8]}-{safe}"
        try:
            self._ensure_bucket()
            self._client.put_object(self._bucket, key, io.BytesIO(content), len(content),
                                    content_type=mimetypes.guess_type(safe)[0] or "application/octet-stream")
        except Exception as error:
            raise ServiceUnavailableError(f"Хранилище файлов недоступно: {error}") from None
        return f"{config.MINIO_PUBLIC_URL.rstrip('/')}/{self._bucket}/{key}"
