from __future__ import annotations

from viraldy.shared.errors.base import AppError, PayloadTooLargeError

ALLOWED_ASSET_TYPES = {"reference", "ugc", "product_media", "other"}


def validate_upload_declaration(
    filename: str,
    declared_mime_type: str,
    declared_size_bytes: int,
    asset_type: str,
    allowed_mime_types: list[str],
    max_size_bytes: int,
) -> None:
    if not filename.strip():
        raise AppError("INVALID_UPLOAD_DECLARATION", "Filename is required.")
    if asset_type not in ALLOWED_ASSET_TYPES:
        raise AppError("INVALID_ASSET_TYPE", "Asset type is not supported.")
    if declared_mime_type not in allowed_mime_types:
        raise AppError("UNSUPPORTED_MIME_TYPE", "Declared MIME type is not supported.")
    if declared_size_bytes <= 0:
        raise AppError("INVALID_UPLOAD_SIZE", "Declared upload size must be positive.")
    if declared_size_bytes > max_size_bytes:
        raise PayloadTooLargeError("UPLOAD_TOO_LARGE", "Declared upload is too large.")
