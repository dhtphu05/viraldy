from .config import get_max_product_image_bytes, get_max_reference_video_bytes
from .errors import SmartRemakeValidationError
from .schemas import UploadedMedia


PRODUCT_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
REFERENCE_VIDEO_MIME_TYPES = {"video/mp4", "video/webm", "video/quicktime"}


def assert_product_image(media: UploadedMedia) -> None:
    if media.mime_type not in PRODUCT_IMAGE_MIME_TYPES:
        raise SmartRemakeValidationError(
            f"Unsupported product image MIME type: {media.mime_type}.",
            "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE",
            {"mimeType": media.mime_type},
        )
    if not media.bytes:
        raise SmartRemakeValidationError("Product image upload is empty.", "INVALID_PRODUCT_LOCK")
    if len(media.bytes) > get_max_product_image_bytes():
        raise SmartRemakeValidationError(
            "Product image exceeds the configured size limit.",
            "SMART_REMAKE_UPLOAD_TOO_LARGE",
        )


def assert_reference_video(media: UploadedMedia) -> None:
    if media.mime_type not in REFERENCE_VIDEO_MIME_TYPES:
        raise SmartRemakeValidationError(
            f"Unsupported reference video MIME type: {media.mime_type}.",
            "UNSUPPORTED_SMART_REMAKE_MEDIA_TYPE",
            {"mimeType": media.mime_type},
        )
    if not media.bytes:
        raise SmartRemakeValidationError("Reference video upload is empty.", "INVALID_SMART_REMAKE_INPUT")
    if len(media.bytes) > get_max_reference_video_bytes():
        raise SmartRemakeValidationError(
            "Reference video exceeds the Smart Remake size limit.",
            "SMART_REMAKE_UPLOAD_TOO_LARGE",
        )
