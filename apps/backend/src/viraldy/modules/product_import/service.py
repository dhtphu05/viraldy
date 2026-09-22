from __future__ import annotations

from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request

import structlog
from fastapi import HTTPException

from viraldy.modules.product_import.mapper import build_product_import_preview
from viraldy.modules.product_import.schemas import ProductImportPreview
from viraldy.modules.product_import.security import open_public_url
from viraldy.shared.errors.base import AppError

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProductLinkImage:
    source_url: str
    title: str
    description: str | None
    bytes: bytes
    mime_type: str
    file_name: str


def create_product_import_preview(source_url: str) -> ProductImportPreview:
    from viraldy.modules.product_import.crawler import crawl_product_url

    try:
        crawl = crawl_product_url(source_url)
    except HTTPException as exc:
        logger.info(
            "product_crawl_rejected",
            source_host=_source_host(source_url),
            status_code=exc.status_code,
        )
        message = str(exc.detail) if exc.status_code in {400, 422, 502} else "Product crawl failed."
        raise AppError(
            "PRODUCT_CRAWL_FAILED",
            message,
            status_code=exc.status_code,
        ) from exc
    except AppError:
        raise
    except Exception as exc:
        logger.exception("product_crawl_failed", source_host=_source_host(source_url))
        raise AppError(
            "PRODUCT_CRAWL_FAILED",
            "Product crawl failed. Try the link again later.",
            status_code=502,
        ) from exc
    return build_product_import_preview(source_url, crawl)


def fetch_product_link_image(source_url: str, *, max_bytes: int) -> ProductLinkImage:
    """Reuse the product crawler to resolve and safely download its primary image."""
    preview = create_product_import_preview(source_url)
    image_url = preview.product_draft.metadata_json.get("image_url")
    if not isinstance(image_url, str) or not image_url:
        raise AppError(
            "PRODUCT_CRAWL_IMAGE_MISSING",
            "We could not find a usable product image at this link.",
            status_code=422,
        )

    try:
        request = Request(  # noqa: S310 - open_public_url validates scheme, host, and redirects.
            image_url,
            headers={"User-Agent": "ViraldyProductImport/1.0"},
        )
        with open_public_url(request, timeout=15) as response:
            content = response.read(max_bytes + 1)
    except AppError:
        raise
    except (OSError, URLError) as exc:
        logger.info("product_image_fetch_failed", source_host=_source_host(source_url))
        raise AppError(
            "PRODUCT_CRAWL_IMAGE_FETCH_FAILED",
            "We could not retrieve the product image from this link.",
            status_code=422,
        ) from exc

    if len(content) > max_bytes:
        raise AppError(
            "PRODUCT_CRAWL_IMAGE_TOO_LARGE",
            "The product image from this link is too large.",
            status_code=413,
        )

    mime_type = _image_mime_type(content)
    if mime_type is None:
        raise AppError(
            "PRODUCT_CRAWL_IMAGE_UNSUPPORTED",
            "The product image from this link is not supported.",
            status_code=422,
        )

    file_name = {
        "image/jpeg": "product-image.jpg",
        "image/png": "product-image.png",
        "image/webp": "product-image.webp",
    }[mime_type]
    return ProductLinkImage(
        source_url=preview.source_url,
        title=preview.product_draft.name,
        description=preview.product_draft.description,
        bytes=content,
        mime_type=mime_type,
        file_name=file_name,
    )


def _source_host(source_url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(source_url).hostname or "unknown"


def _image_mime_type(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None
