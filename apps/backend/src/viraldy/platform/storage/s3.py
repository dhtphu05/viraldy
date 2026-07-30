from __future__ import annotations

from datetime import timedelta

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from viraldy.platform.clock.utc import utc_now
from viraldy.platform.config.settings import Settings
from viraldy.platform.storage.ports import ObjectMetadata, PresignedUpload, StoredObject


class S3StorageAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client(
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
                s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"}
            ),
        )

    def check_health(self) -> bool:
        self._client.head_bucket(Bucket=self._settings.s3_bucket)
        return True

    def create_presigned_upload(self, key: str, content_type: str) -> PresignedUpload:
        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._settings.s3_bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=self._settings.s3_presigned_expiry_seconds,
        )
        return PresignedUpload(
            url=url,
            method="PUT",
            required_headers={"Content-Type": content_type},
            expires_at=utc_now() + timedelta(seconds=self._settings.s3_presigned_expiry_seconds),
        )

    def create_presigned_download(self, key: str) -> str:
        return str(
            self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._settings.s3_bucket, "Key": key},
                ExpiresIn=self._settings.s3_presigned_expiry_seconds,
            )
        )

    def object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._settings.s3_bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise

    def get_object_metadata(self, key: str) -> ObjectMetadata:
        response = self._client.head_object(Bucket=self._settings.s3_bucket, Key=key)
        metadata = response.get("Metadata") or {}
        return ObjectMetadata(
            size_bytes=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
            checksum_sha256=metadata.get("checksum_sha256"),
        )

    def download_object(self, key: str, destination_path: str) -> None:
        self._client.download_file(self._settings.s3_bucket, key, destination_path)

    def upload_file(self, source_path: str, key: str, content_type: str) -> None:
        self._client.upload_file(
            source_path,
            self._settings.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._settings.s3_bucket, Key=key)

    def list_objects(self, prefix: str) -> list[StoredObject]:
        objects: list[StoredObject] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=self._settings.s3_bucket,
            Prefix=prefix,
        ):
            for item in page.get("Contents", []):
                objects.append(
                    StoredObject(
                        key=str(item["Key"]),
                        last_modified=item["LastModified"],
                        size_bytes=int(item["Size"]),
                    )
                )
        return objects
