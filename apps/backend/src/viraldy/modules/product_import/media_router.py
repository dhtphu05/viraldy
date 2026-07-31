from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from viraldy.shared.errors.base import NotFoundError

router = APIRouter(prefix="/outputs/renders", tags=["product-crawl-media"])


@router.get("/{filename}")
async def serve_product_crawl_media(filename: str) -> FileResponse:
    if (
        filename != Path(filename).name
        or not filename.startswith("review-clip-")
        or not filename.endswith(".mp4")
    ):
        raise NotFoundError("PRODUCT_CRAWL_MEDIA_NOT_FOUND")
    output_dir = Path(
        os.environ.get(
            "PRODUCT_CRAWL_OUTPUT_DIR",
            str(Path(tempfile.gettempdir()) / "viraldy-product-crawl"),
        )
    ).resolve()
    file_path = (output_dir / filename).resolve()
    if file_path.parent != output_dir or not file_path.is_file():
        raise NotFoundError("PRODUCT_CRAWL_MEDIA_NOT_FOUND")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        headers={"Cache-Control": "public, max-age=3600"},
    )
