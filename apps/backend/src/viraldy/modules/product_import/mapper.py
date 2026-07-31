from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import cast
from urllib.parse import parse_qs, urlsplit

from viraldy.modules.product_import.schemas import ProductImportPreview
from viraldy.modules.products.contracts import (
    CommercialContextV1,
    ProductContextV1,
    ProductFeatureV1,
    ProductIdentityV1,
)
from viraldy.modules.products.schemas import CreateProductRequest
from viraldy.shared.errors.base import AppError

_EMPTY_VALUES = frozenset({"", "n/a", "unknown", "unknown product"})
_CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}


def build_product_import_preview(
    source_url: str,
    crawl: dict[str, object],
) -> ProductImportPreview:
    markdown = _text(crawl.get("markdown"))
    name = _observed_text(crawl.get("title"))
    if name.lower() == "generic web page":
        name = _markdown_heading(markdown)
    if not name:
        raise AppError(
            "PRODUCT_CRAWL_DATA_INCOMPLETE",
            "The crawler did not return a product title.",
            status_code=422,
        )

    description = _observed_text(crawl.get("description"))
    brand = _markdown_value(markdown, "Brand") or _markdown_value(markdown, "Developer")
    category = _markdown_value(markdown, "Category")
    inventory = _markdown_value(markdown, "Inventory")
    original_price_text = _observed_text(crawl.get("originalPrice")) or _markdown_price(
        markdown, "Original Price"
    )
    current_price_text = (
        _observed_text(crawl.get("salePrice"))
        or _markdown_price(markdown, "Discounted/Current Price")
        or original_price_text
    )
    current_price, currency = _parse_money(current_price_text)
    original_price, original_currency = _parse_money(original_price_text)
    currency = currency or original_currency
    compare_at_price = (
        original_price
        if original_price is not None
        and current_price is not None
        and original_price != current_price
        else None
    )

    source_type = _source_type(source_url, crawl)
    external_id = _external_id(source_url, crawl, markdown, source_type)
    screenshots = _string_list(crawl.get("screenshots"))
    videos = _string_list(crawl.get("videos"))
    image_url = _observed_text(crawl.get("image")) or (screenshots[0] if screenshots else None)
    features = [
        ProductFeatureV1(
            id=f"crawl-feature-{index}",
            label=value[:160],
            description=value,
        )
        for index, value in enumerate(_markdown_features(markdown), start=1)
    ]

    identity = ProductIdentityV1(
        name=name[:255],
        brand=brand or None,
        category=(category or "unknown")[:120],
        market="unknown",
        currency=currency,
    )
    product_context = ProductContextV1(
        identity=identity,
        features=features,
        commercial=CommercialContextV1(
            price=current_price,
            compare_at_price=compare_at_price,
            discount_text=_observed_text(
                crawl.get("discountText") or crawl.get("discount")
            ),
        ),
    )
    metadata = _metadata_from_crawl(
        source_url=source_url,
        crawl=crawl,
        brand=brand,
        category=category,
        inventory=inventory,
        image_url=image_url,
        screenshots=screenshots,
        videos=videos,
        current_price=current_price_text,
        original_price=original_price_text,
        currency=currency,
    )
    draft = CreateProductRequest(
        name=identity.name,
        description=description,
        market=identity.market,
        external_source=source_type,
        external_id=external_id,
        metadata_json=metadata,
        product_context=product_context,
    )
    return ProductImportPreview(source_url=source_url, crawl=crawl, product_draft=draft)


def _metadata_from_crawl(
    *,
    source_url: str,
    crawl: dict[str, object],
    brand: str,
    category: str,
    inventory: str,
    image_url: str | None,
    screenshots: list[str],
    videos: list[str],
    current_price: str,
    original_price: str,
    currency: str | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "source_url": source_url,
        "source_type": _source_type(source_url, crawl),
        "brand": brand,
        "category": category,
        "inventory": inventory,
        "image_url": image_url or "",
        "screenshots": screenshots,
        "videos": videos,
        "rating": _observed_text(crawl.get("rating")),
        "reviews_count": _observed_text(
            crawl.get("reviews_count") or crawl.get("reviewsCount")
        ),
        "reviews": _json_list(crawl.get("reviews")),
        "review_cards": _json_list(crawl.get("review_cards")),
        "customer_say": _observed_text(crawl.get("customer_say")),
        "buyer_images": _string_list(
            crawl.get("buyer_images") or crawl.get("review_images")
        ),
        "review_videos": _string_list(
            crawl.get("review_videos") or crawl.get("reviewVideos")
        ),
        "crawl_confidence": crawl.get("confidence") or 0,
        "crawl_markdown": _text(crawl.get("markdown")),
        "current_price_text": current_price,
        "original_price_text": original_price,
        "currency": currency or "",
        "coupon_code": _observed_text(crawl.get("couponCode")),
        "discount_text": _observed_text(
            crawl.get("discountText") or crawl.get("discount")
        ),
        "promo_headline": _observed_text(crawl.get("promoHeadline")),
        "promo_bullets": _string_list(crawl.get("promoBullets")),
        "cta_text": _observed_text(crawl.get("ctaText")),
        "is_coupon": bool(crawl.get("isCoupon")),
    }
    return metadata


def _external_id(
    source_url: str,
    crawl: dict[str, object],
    markdown: str,
    source_type: str,
) -> str | None:
    parent_asin = _observed_text(crawl.get("parent_asin") or crawl.get("parentAsin"))
    if parent_asin:
        return parent_asin
    if source_type == "amazon":
        match = re.search(r"\*\*ASIN\*\*:\s*`?([A-Z0-9]{10})", markdown, re.IGNORECASE)
        if not match:
            match = re.search(r"(?:/dp/|/gp/product/|/d/)([A-Z0-9]{10})", source_url)
        return match.group(1).upper() if match else None
    if source_type in {"koupon", "dealseek", "affitfy"}:
        target_url = _observed_text(crawl.get("targetUrl"))
        match = re.search(r"(?:/dp/|/gp/product/|/d/)([A-Z0-9]{10})", target_url)
        return match.group(1).upper() if match else None
    if "apps.apple.com" in source_url:
        match = re.search(r"/id(\d+)", source_url)
        return match.group(1) if match else None
    if "play.google.com" in source_url:
        return parse_qs(urlsplit(source_url).query).get("id", [None])[0]
    return None


def _markdown_value(markdown: str, label: str) -> str:
    match = re.search(
        rf"^\s*-\s*\*\*{re.escape(label)}\*\*:\s*(.+?)\s*$",
        markdown,
        re.IGNORECASE | re.MULTILINE,
    )
    return _observed_text(match.group(1).strip("` ")) if match else ""


def _markdown_heading(markdown: str) -> str:
    match = re.search(r"^\s*#\s+(.+?)\s*$", markdown, re.MULTILINE)
    return _observed_text(match.group(1)) if match else ""


def _source_type(source_url: str, crawl: dict[str, object]) -> str:
    hostname = (urlsplit(source_url).hostname or "").lower()
    for source in ("koupon", "dealseek", "affitfy"):
        if source in hostname:
            return source
    return _observed_text(crawl.get("sourceType")) or "website"


def _markdown_price(markdown: str, label: str) -> str:
    match = re.search(
        rf"^\s*-\s*{re.escape(label)}:\s*`?([^`\n]*)`?\s*$",
        markdown,
        re.IGNORECASE | re.MULTILINE,
    )
    return _observed_text(match.group(1)) if match else ""


def _markdown_features(markdown: str) -> list[str]:
    match = re.search(
        r"^##\s+Features \(Bullet Points\)\s*$([\s\S]*?)(?=^##\s+|\Z)",
        markdown,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return []
    return [
        value
        for value in (
            _observed_text(line.removeprefix("-").strip())
            for line in match.group(1).splitlines()
            if line.strip().startswith("-")
        )
        if value
    ][:20]


def _parse_money(value: str) -> tuple[Decimal | None, str | None]:
    text = value.strip()
    if not text or text.lower() == "free":
        return None, None
    upper = text.upper()
    currency = next(
        (code for token, code in _CURRENCY_SYMBOLS.items() if token in text),
        None,
    )
    if currency is None:
        currency = next(
            (code for code in ("USD", "VND", "EUR", "GBP", "JPY") if code in upper),
            None,
        )
    numeric = re.sub(r"[^\d,.-]", "", text)
    if not numeric:
        return None, currency
    if currency in {"VND", "JPY"}:
        numeric = numeric.replace(",", "").split(".", maxsplit=1)[0]
    elif "," in numeric and "." in numeric:
        numeric = numeric.replace(",", "")
    elif numeric.count(",") == 1 and len(numeric.rsplit(",", 1)[1]) in {1, 2}:
        numeric = numeric.replace(",", ".")
    else:
        numeric = numeric.replace(",", "")
    try:
        amount = Decimal(numeric)
    except InvalidOperation:
        return None, currency
    return (amount if amount >= 0 else None), currency


def _observed_text(value: object) -> str:
    text = _text(value).strip().strip("`")
    return "" if text.lower() in _EMPTY_VALUES else text


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        text = _observed_text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _json_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []
