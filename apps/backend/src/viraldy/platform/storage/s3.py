from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import ObjectMetadata, PresignedUpload, StoredObject
from viraldy.shared.errors.base import AppError

# Keep workspace/project ownership prefixes unchanged for both storage backends.
R2_OBJECT_MARKER = "/__r2__/"


class S3StorageAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self._r2_client = None

    @property
    def smart_remake_r2_enabled(self) -> bool:
        return self._settings.r2_configured

    def _object_store(self, key: str = "") -> tuple[Any, str]:
        if R2_OBJECT_MARKER in key:
            if not self._settings.r2_configured:
                raise AppError(
                    "SMART_REMAKE_R2_NOT_CONFIGURED",
                    "Private R2 storage is not configured. "
                    "Configure the R2 account, bucket and credentials.",
                    503,
                )
            if self._r2_client is None:
                self._r2_client = boto3.client(
                    "s3",
                    endpoint_url=f"https://{self._settings.r2_account_id}.r2.cloudflarestorage.com",
                    region_name="auto",
                    aws_access_key_id=self._settings.r2_access_key_id.get_secret_value()
                    if self._settings.r2_access_key_id
                    else None,
                    aws_secret_access_key=self._settings.r2_secret_access_key.get_secret_value()
                    if self._settings.r2_secret_access_key
                    else None,
                    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
                )
            return self._r2_client, str(self._settings.r2_bucket)
        if self._client is None:
            self._client = self._legacy_client()
        return self._client, self._settings.s3_bucket

    def _legacy_client(self) -> Any:
        settings = self._settings
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id.get_secret_value()
            if settings.s3_access_key_id
            else None,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value()
            if settings.s3_secret_access_key
            else None,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"},
            ),
        )

    def check_health(self) -> bool:
        client, bucket = self._object_store()
        client.head_bucket(Bucket=bucket)
        return True

    def create_presigned_upload(
        self, key: str, content_type: str, *, content_length: int | None = None
    ) -> PresignedUpload:
        client, bucket = self._object_store(key)
        params: dict[str, Any] = {"Bucket": bucket, "Key": key, "ContentType": content_type}
        if content_length is not None:
            params["ContentLength"] = content_length
        url = client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=self._settings.s3_presigned_expiry_seconds,
        )
        return PresignedUpload(
            url=url,
            method="PUT",
            required_headers={"Content-Type": content_type},
            expires_at=utc_now() + timedelta(seconds=self._settings.s3_presigned_expiry_seconds),
        )

    def create_presigned_download(self, key: str, *, filename: str | None = None) -> str:
        client, bucket = self._object_store(key)
        params = {"Bucket": bucket, "Key": key}
        if filename:
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)[:160] or "download"
            params["ResponseContentDisposition"] = f'attachment; filename="{safe_name}"'
        return str(
            client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=self._settings.s3_presigned_expiry_seconds,
            )
        )

    def object_exists(self, key: str) -> bool:
        client, bucket = self._object_store(key)
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        client, bucket = self._object_store(key)
        response = client.head_object(Bucket=bucket, Key=key)
        metadata = response.get("Metadata") or {}
        return ObjectMetadata(
            size_bytes=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
            checksum_sha256=metadata.get("checksum_sha256"),
        )

    def download_object(self, key: str, destination_path: str) -> None:
        client, bucket = self._object_store(key)
        client.download_file(bucket, key, destination_path)

    def read_object_bytes(self, key: str, maximum_bytes: int) -> bytes:
        client, bucket = self._object_store(key)
        response = client.get_object(Bucket=bucket, Key=key, Range=f"bytes=0-{maximum_bytes}")
        body = response["Body"]
        try:
            return bytes(body.read(maximum_bytes + 1))
        finally:
            body.close()

    def upload_file(self, source_path: str, key: str, content_type: str) -> None:
        client, bucket = self._object_store(key)
        client.upload_file(
            source_path,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def delete_object(self, key: str) -> None:
        client, bucket = self._object_store(key)
        client.delete_object(Bucket=bucket, Key=key)

    def list_objects(self, prefix: str) -> list[StoredObject]:
        objects: dict[str, StoredObject] = {}
        stores = [(self._object_store(prefix), R2_OBJECT_MARKER in prefix)]
        if self._settings.r2_configured and R2_OBJECT_MARKER not in prefix:
            stores.append((self._object_store(f"{prefix.rstrip('/')}{R2_OBJECT_MARKER}"), True))
        for (client, bucket), is_r2 in stores:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    key = str(item["Key"])
                    if is_r2 and R2_OBJECT_MARKER not in key:
                        continue
                    objects[key] = StoredObject(
                        key=key, last_modified=item["LastModified"], size_bytes=int(item["Size"])
                    )
        return list(objects.values())
