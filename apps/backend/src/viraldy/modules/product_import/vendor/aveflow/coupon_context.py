import re


_PRICE_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")


def _normalize_discount_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip().upper().replace(" ", "")
    if cleaned.endswith("%"):
        return f"{cleaned} OFF"
    if cleaned.startswith("$"):
        return f"{cleaned} OFF"
    return value.strip().upper()


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def extract_coupon_context(markdown: str, html: str = "") -> dict[str, object]:
    text = " ".join(part for part in (markdown or "", _strip_html(html)) if part)
    text = re.sub(r"\s+", " ", text).strip()

    coupon_code = ""
    discount_text = ""
    sale_price = ""
    original_price = ""

    code_match = re.search(r"\b(?:code|coupon(?:\s+code)?)\s*[:\-]?\s*([A-Z0-9]{4,20})\b", text, re.I)
    if code_match:
        coupon_code = code_match.group(1).upper()

    discount_match = re.search(r"\bSave\s+(\d{1,3}%|\$\s?\d[\d,]*(?:\.\d{2})?)(?:\b|\s)", text, re.I)
    if not discount_match:
        discount_match = re.search(r"\b(\d{1,3}%)\s+off\b", text, re.I)
    if discount_match:
        discount_text = _normalize_discount_text(discount_match.group(1))

    was_now_match = re.search(
        r"\bWas\s*(" + _PRICE_RE.pattern + r")\s*,?\s*now\s*(" + _PRICE_RE.pattern + r")\b",
        text,
        re.I,
    )
    if was_now_match:
        original_price = was_now_match.group(1).replace(" ", "")
        sale_price = was_now_match.group(2).replace(" ", "")
    else:
        prices = [price.replace(" ", "") for price in _PRICE_RE.findall(text)]
        if prices:
            sale_price = prices[-1]
            if len(prices) > 1:
                original_price = prices[0]

    promo_headline = ""
    headline_match = re.search(r"([^.!?]*\b(?:save|coupon|code)\b[^.!?]*[.!?])", text, re.I)
    if headline_match:
        promo_headline = headline_match.group(1).strip()

    promo_bullets = []
    if discount_text:
        promo_bullets.append(discount_text)
    if sale_price and original_price and sale_price != original_price:
        promo_bullets.append(f"Was {original_price}, now {sale_price}")

    cta_text = f"Use code {coupon_code}" if coupon_code else ""

    return {
        "coupon_code": coupon_code,
        "discount_text": discount_text,
        "original_price": original_price,
        "sale_price": sale_price,
        "promo_headline": promo_headline,
        "promo_bullets": promo_bullets,
        "cta_text": cta_text,
    }
