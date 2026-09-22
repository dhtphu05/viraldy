from __future__ import annotations

from decimal import Decimal
from socket import AF_INET, SOCK_STREAM
from uuid import uuid4

import pytest

from viraldy.modules.product_import import service as product_import_service
from viraldy.modules.product_import.mapper import build_product_import_preview
from viraldy.modules.product_import.schemas import ProductCrawlRequest
from viraldy.modules.product_import.security import (
    PublicHttpRedirectHandler,
    validate_public_http_url,
)
from viraldy.modules.products import router as products_router
from viraldy.shared.errors.base import AppError


def _public_resolver(
    host: str,
    port: int,
    *,
    type: int,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    assert host == "shop.example.com"
    assert port == 443
    assert type == SOCK_STREAM
    return [(AF_INET, SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _private_resolver(
    host: str,
    port: int,
    *,
    type: int,
) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(AF_INET, SOCK_STREAM, 6, "", ("10.0.0.4", port))]


def test_product_crawl_url_accepts_public_https_and_removes_fragment() -> None:
    result = validate_public_http_url(
        "https://shop.example.com/products/one?variant=blue#reviews",
        resolver=_public_resolver,
    )

    assert result == "https://shop.example.com/products/one?variant=blue"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://169.254.169.254/latest/meta-data",
        "https://user:password@shop.example.com/product",
        "https://localhost/product",
    ],
)
def test_product_crawl_url_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(AppError) as captured:
        validate_public_http_url(url, resolver=_public_resolver)

    assert captured.value.code == "PRODUCT_CRAWL_URL_INVALID"
    assert captured.value.status_code == 400


def test_product_crawl_url_rejects_hostname_resolving_to_private_ip() -> None:
    with pytest.raises(AppError) as captured:
        validate_public_http_url(
            "https://shop.example.com/product",
            resolver=_private_resolver,
        )

    assert captured.value.code == "PRODUCT_CRAWL_URL_INVALID"


def test_product_crawl_redirect_rejects_private_target() -> None:
    handler = PublicHttpRedirectHandler()

    with pytest.raises(AppError) as captured:
        handler.redirect_request(
            req=object(),  # type: ignore[arg-type]
            fp=None,
            code=302,
            msg="Found",
            headers={},
            newurl="http://169.254.169.254/latest/meta-data",
        )

    assert captured.value.code == "PRODUCT_CRAWL_URL_INVALID"


def test_amazon_crawl_maps_only_observed_product_context() -> None:
    preview = build_product_import_preview(
        "https://www.amazon.com/dp/B0TEST1234",
        {
            "title": "Observed Candle Warmer",
            "description": "A dimmable candle warmer with a timer.",
            "image": "https://images.example.test/main.jpg",
            "screenshots": [
                "https://images.example.test/main.jpg",
                "https://images.example.test/detail.jpg",
            ],
            "videos": ["https://video.example.test/demo.mp4"],
            "sourceType": "amazon",
            "confidence": 0.9,
            "rating": "4.7",
            "reviews_count": "8931",
            "parent_asin": "B0PARENT01",
            "reviews": [{"title": "Useful", "body": "The timer works."}],
            "markdown": """
# Product Details: Observed Candle Warmer
- **ASIN**: `B0TEST1234`
- **Brand**: Example Brand
- **Category**: Home & Kitchen > Candle Lamps
- **Inventory**: In Stock
- **Price**:
  - Original Price: `$39.99`
  - Discounted/Current Price: `$29.99`

## Features (Bullet Points)
- Dimmable light
- Automatic timer

## Specifications
| Technical Property | Detail Specification |
""",
        },
    )

    draft = preview.product_draft
    context = draft.product_context

    assert draft.name == "Observed Candle Warmer"
    assert draft.external_source == "amazon"
    assert draft.external_id == "B0PARENT01"
    assert draft.metadata_json["source_url"] == "https://www.amazon.com/dp/B0TEST1234"
    assert draft.metadata_json["image_url"] == "https://images.example.test/main.jpg"
    assert draft.metadata_json["rating"] == "4.7"
    assert context is not None
    assert context.identity.brand == "Example Brand"
    assert context.identity.category == "Home & Kitchen > Candle Lamps"
    assert context.identity.market == "unknown"
    assert context.identity.currency == "USD"
    assert context.commercial.price == Decimal("29.99")
    assert context.commercial.compare_at_price == Decimal("39.99")
    assert [feature.label for feature in context.features] == [
        "Dimmable light",
        "Automatic timer",
    ]
    assert context.benefits == []
    assert context.personas == []
    assert context.governance.claims == []


def test_app_store_crawl_uses_store_identifier_without_inventing_commercial_data() -> None:
    preview = build_product_import_preview(
        "https://apps.apple.com/us/app/example/id123456789",
        {
            "title": "Example App",
            "description": "A real app description.",
            "sourceType": "app_store",
            "markdown": """
# Example App
## General Information
- **Platform**: Apple App Store
- **Developer**: Example Studio
- **Category**: Utilities
- **Price**: Free
""",
        },
    )

    draft = preview.product_draft
    context = draft.product_context

    assert draft.external_source == "app_store"
    assert draft.external_id == "123456789"
    assert context is not None
    assert context.identity.brand == "Example Studio"
    assert context.identity.category == "Utilities"
    assert context.commercial.price is None


def test_generic_website_uses_observed_markdown_heading() -> None:
    preview = build_product_import_preview(
        "https://shop.example.com/products/observed",
        {
            "title": "Generic Web Page",
            "sourceType": "website",
            "markdown": "# Observed Website Product\n\nObserved page copy.",
        },
    )

    assert preview.product_draft.name == "Observed Website Product"
    assert preview.product_draft.external_source == "website"


def test_product_link_image_reuses_crawl_preview_and_validates_downloaded_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = build_product_import_preview(
        "https://shop.example.com/products/observed",
        {
            "title": "Observed Product",
            "description": "A product from the page.",
            "image": "https://images.example.com/product.png",
            "sourceType": "website",
            "markdown": "# Observed Product",
        },
    )

    class ImageResponse:
        def __enter__(self) -> ImageResponse:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            assert limit == 1_001
            return b"\x89PNG\r\n\x1a\nproduct-image"

    monkeypatch.setattr(
        product_import_service,
        "create_product_import_preview",
        lambda _url: preview,
    )
    monkeypatch.setattr(
        product_import_service,
        "open_public_url",
        lambda _request, *, timeout: ImageResponse(),
    )

    image = product_import_service.fetch_product_link_image(
        "https://shop.example.com/products/observed",
        max_bytes=1_000,
    )

    assert image.source_url == preview.source_url
    assert image.title == "Observed Product"
    assert image.description == "A product from the page."
    assert image.mime_type == "image/png"
    assert image.file_name == "product-image.png"


def test_deal_source_and_target_asin_are_preserved() -> None:
    preview = build_product_import_preview(
        "https://www.koupon.ai/product/fixture",
        {
            "title": "Fixture Deal",
            "sourceType": "amazon",
            "targetUrl": "https://www.amazon.com/dp/B0TEST1234",
            "isCoupon": True,
            "couponCode": "SAVE20",
            "markdown": "# Coupon Product: Fixture Deal",
        },
    )

    assert preview.product_draft.external_source == "koupon"
    assert preview.product_draft.external_id == "B0TEST1234"
    assert preview.product_draft.metadata_json["coupon_code"] == "SAVE20"


@pytest.mark.asyncio
async def test_crawl_preview_endpoint_returns_create_product_compatible_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview = build_product_import_preview(
        "https://shop.example.com/product",
        {
            "title": "Observed Product",
            "sourceType": "website",
            "markdown": "# Observed Product",
        },
    )

    async def allow_permission(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(products_router, "require_workspace_permission", allow_permission)
    monkeypatch.setattr(
        products_router,
        "validate_public_http_url",
        lambda url: url,
    )
    monkeypatch.setattr(
        products_router,
        "create_product_import_preview",
        lambda _url: preview,
    )

    response = await products_router.crawl_product_preview(
        workspace_id=uuid4(),
        payload=ProductCrawlRequest(url="https://shop.example.com/product"),
        current_user=object(),  # type: ignore[arg-type]
        db=object(),  # type: ignore[arg-type]
        request_id="req-product-preview",
    )

    assert response.error is None
    assert response.data["crawl"]["title"] == "Observed Product"
    assert response.data["product_draft"]["name"] == "Observed Product"
    assert response.meta.request_id == "req-product-preview"
