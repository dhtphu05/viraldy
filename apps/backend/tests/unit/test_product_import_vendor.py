from __future__ import annotations

from pathlib import Path

import pytest

from viraldy.modules.product_import.crawler import amazon_product_page_blocked
from viraldy.modules.product_import.vendor.aveflow import app_store
from viraldy.modules.product_import.vendor.aveflow.amazon import parse_amazon_product
from viraldy.modules.product_import.vendor.aveflow.coupon import (
    extract_affitfy_data,
    extract_dealseek_data,
    extract_koupon_data,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "product_import"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_vendored_amazon_parser_regression() -> None:
    parsed = parse_amazon_product(
        _fixture("amazon_product.html"),
        "https://www.amazon.com/dp/B0TEST1234",
    )

    assert parsed["asin"] == "B0TEST1234"
    assert parsed["parent_asin"] == "B0PARENT01"
    assert parsed["title"] == "Observed Candle Warmer"
    assert parsed["brand"] == "Example Brand"
    assert parsed["categories"] == "Home & Kitchen > Candle Lamps"
    assert parsed["price"] == {"original": "$39.99", "discounted": "$29.99"}
    assert parsed["bullet_points"] == ["Dimmable light", "Automatic timer"]


def test_vendored_apple_parser_regression_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_store,
        "_fetch_itunes_lookup",
        lambda _app_id: {
            "trackName": "Fixture Apple App",
            "description": "Fixture description",
            "artistName": "Fixture Studio",
            "primaryGenreName": "Utilities",
            "averageUserRating": 4.9,
            "userRatingCount": 321,
            "artworkUrl512": "https://is1-ssl.mzstatic.com/image/100x100bb/icon.png",
            "releaseNotes": "Fixture release",
            "fileSizeBytes": "1048576",
            "price": 0,
            "currency": "USD",
            "screenshotUrls": ["https://images.example.test/apple-one.png"],
            "ipadScreenshotUrls": [],
        },
    )

    parsed = app_store.parse_app_store(
        _fixture("apple_app.html"),
        "https://apps.apple.com/us/app/fixture/id123456789",
    )

    assert parsed["title"] == "Fixture Apple App"
    assert parsed["developer"] == "Fixture Studio"
    assert parsed["price"] == "Free"
    assert parsed["screenshots"] == ["https://images.example.test/apple-one.png"]
    assert parsed["reviews_list"][0]["body"] == "The timer works."


def test_vendored_google_play_parser_regression() -> None:
    parsed = app_store.parse_app_store(
        _fixture("google_play.html"),
        "https://play.google.com/store/apps/details?id=com.example.fixture",
    )

    assert parsed["title"] == "Fixture Play App"
    assert parsed["developer"] == "Fixture Studio"
    assert parsed["category"] == "Utilities"
    assert parsed["price"] == "Free"
    assert parsed["rating"] == "4.8"
    assert parsed["screenshots"] == [
        "https://play-lh.googleusercontent.com/screenshot=s0"
    ]


def test_vendored_koupon_parser_regression() -> None:
    parsed = extract_koupon_data(
        _fixture("koupon.html"),
        "https://www.koupon.ai/product/fixture",
    )

    assert parsed["asin"] == "B0TEST1234"
    assert parsed["couponCode"] == "SAVE20"
    assert parsed["discount"] == "20% OFF"
    assert parsed["originalPrice"] == "$39.99"
    assert parsed["salePrice"] == "$31.99"
    assert parsed["targetUrl"] == "https://www.amazon.com/dp/B0TEST1234"


def test_vendored_dealseek_parser_regression() -> None:
    parsed = extract_dealseek_data(
        "",
        "https://dealseek.com/deal?dealHash="
        "B0TEST1234-A1B2C3D4E5F6G7-50.00-35.00-SAVE30",
    )

    assert parsed["asin"] == "B0TEST1234"
    assert parsed["couponCode"] == "SAVE30"
    assert parsed["discount"] == "30% OFF"
    assert parsed["targetUrl"] == (
        "https://www.amazon.com/dp/B0TEST1234?m=A1B2C3D4E5F6G7"
    )


def test_vendored_affitfy_parser_regression_without_network() -> None:
    parsed = extract_affitfy_data(
        _fixture("affitfy.html"),
        "https://affitfy.com/deals/fixture",
    )

    assert parsed["asin"] == "B0TEST5678"
    assert parsed["couponCode"] == "SAVE25"
    assert parsed["title"] == "Fixture Affitfy Deal"
    assert parsed["targetUrl"] == "https://www.amazon.com/dp/B0TEST5678"


def test_amazon_bot_check_is_not_accepted_as_product_data() -> None:
    assert amazon_product_page_blocked(
        "<html>Sorry, we just need to make sure you're not a robot</html>"
    )
    assert not amazon_product_page_blocked(
        '<html><span id="productTitle">Observed Product</span></html>'
    )
