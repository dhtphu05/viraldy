from __future__ import annotations

import structlog
from fastapi import HTTPException

from viraldy.modules.product_import.mapper import build_product_import_preview
from viraldy.modules.product_import.schemas import ProductImportPreview
from viraldy.shared.errors.base import AppError

logger = structlog.get_logger(__name__)


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


def _source_host(source_url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(source_url).hostname or "unknown"
