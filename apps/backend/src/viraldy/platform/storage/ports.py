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


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    last_modified: datetime
    size_bytes: int


class StoragePort(Protocol):
    def check_health(self) -> bool:
        raise NotImplementedError

    def create_presigned_upload(self, key: str, content_type: str) -> PresignedUpload:
        raise NotImplementedError

    def create_presigned_download(self, key: str) -> str:
        raise NotImplementedError

    def object_exists(self, key: str) -> bool:
        raise NotImplementedError

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        raise NotImplementedError

    def download_object(self, key: str, destination_path: str) -> None:
        raise NotImplementedError

    def upload_file(self, source_path: str, key: str, content_type: str) -> None:
        raise NotImplementedError

    def delete_object(self, key: str) -> None:
        raise NotImplementedError

    def list_objects(self, prefix: str) -> list[StoredObject]:
        raise NotImplementedError
