from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    method: str
    required_headers: dict[str, str]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    size_bytes: int
    content_type: str | None
    checksum_sha256: str | None = None


class StoragePort(Protocol):
    def create_presigned_upload(self, key: str, content_type: str) -> PresignedUpload:
        raise NotImplementedError

    def create_presigned_download(self, key: str) -> str:
        raise NotImplementedError

    def object_exists(self, key: str) -> bool:
        raise NotImplementedError

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        raise NotImplementedError

    def delete_object(self, key: str) -> None:
        raise NotImplementedError
