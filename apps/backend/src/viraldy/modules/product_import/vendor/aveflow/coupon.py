import re
import json
from bs4 import BeautifulSoup

def extract_koupon_data(html_content: str, url: str) -> dict:
    """
    Parses Koupon.ai product page HTML and extracts coupon details.
    Uses __NEXT_DATA__ if available for clean structured data, with DOM parsing as a fallback.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {
        "isCoupon": True,
        "couponCode": "",
        "discount": "",
        "originalPrice": "",
        "salePrice": "",
        "targetUrl": "",
        "title": "",
        "description": "",
        "image": "",
        "screenshots": [],
        "sourceType": "koupon",
        "brand": "",
        "asin": ""
    }

    # Try __NEXT_DATA__ JSON extraction first
    next_data_elem = soup.find("script", id="__NEXT_DATA__")
    if next_data_elem:
        try:
            next_json = json.loads(next_data_elem.string)
            page_props = next_json.get("props", {}).get("pageProps", {})
            deal = page_props.get("deal", {})
            if deal:
                data["title"] = deal.get("title") or ""
                data["asin"] = deal.get("id") or ""
                data["couponCode"] = deal.get("code") or ""

                # Discount
                disc = deal.get("discount")
                if disc:
                    data["discount"] = f"{disc}% OFF"

                # Pricing
                price = deal.get("price")
                if price is not None:
                    data["salePrice"] = f"${price}" if isinstance(price, (int, float)) or not str(price).startswith('$') else str(price)

                comp_price = deal.get("comparedPrice")
                if comp_price is not None:
                    data["originalPrice"] = f"${comp_price}" if isinstance(comp_price, (int, float)) or not str(comp_price).startswith('$') else str(comp_price)

                # Target URL
                data["targetUrl"] = deal.get("productLink") or ""

                # Brand
                data["brand"] = deal.get("brand") or ""

                # Images
                data["image"] = deal.get("mainImage") or ""
                deal_imgs = deal.get("images", [])
                if isinstance(deal_imgs, list):
                    data["screenshots"] = [img.get("url") for img in deal_imgs if isinstance(img, dict) and img.get("url")]

                # Description
                data["description"] = deal.get("description") or ""

                print(f"[Koupon Crawler] Extracted from JSON: code={data['couponCode']}, discount={data['discount']}, targetUrl={data['targetUrl']}")
                return data
        except Exception as e:
            print(f"[Koupon Crawler] JSON parse error: {e}")

    # Fallback to DOM parsing
    print("[Koupon Crawler] Falling back to DOM parsing")

    # Title
    title_elem = soup.find('h1') or soup.find(class_=re.compile("title", re.I))
    if title_elem:
        data["title"] = title_elem.text.strip()

    # Coupon code
    # Usually in elements with classes like "promo-code" or "code"
    code_elem = soup.select_one(".promo-code, .coupon-code, .copy-code")
    if code_elem:
        data["couponCode"] = code_elem.text.strip()
    else:
        # Try to find uppercase alphanumeric code in text
        # Look for buttons or text containing "Copy"
        for btn in soup.find_all(text=re.compile("copy", re.I)):
            parent = btn.parent
            siblings = list(parent.parent.children)
            for s in siblings:
                if hasattr(s, 'text') and s.text.strip().isupper() and 5 <= len(s.text.strip()) <= 15:
                    data["couponCode"] = s.text.strip()
                    break
            if data["couponCode"]:
                break

    # Discount
    disc_elem = soup.select_one(".discount, .discount-percent, .badge-discount")
    if disc_elem:
        data["discount"] = disc_elem.text.strip()

    # Prices
    sale_elem = soup.select_one(".deal-price, .price-sale, .sale-price")
    if sale_elem:
        data["salePrice"] = sale_elem.text.strip()

    orig_elem = soup.select_one(".list-price, .compared-price, .original-price")
    if orig_elem:
        data["originalPrice"] = orig_elem.text.strip()

    # Target URL
    # Look for amazon.com redirect links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "amazon.com" in href or "amzn.to" in href:
            data["targetUrl"] = href
            break

    # Main Image
    img_elem = soup.find('img', class_=re.compile("main|primary|deal", re.I))
    if img_elem and img_elem.get('src'):
        data["image"] = img_elem['src']

    return data


def extract_dealseek_data(html_content: str, url: str) -> dict:
    """
    Parses dealseek.com details.
    First tries to extract from URL query params (dealHash) which is fast and robust.
    Falls back to DOM/JSON extraction if possible.
    """
    import urllib.parse
    data = {
        "isCoupon": True,
        "couponCode": "",
        "discount": "",
        "originalPrice": "",
        "salePrice": "",
        "targetUrl": "",
        "title": "",
        "description": "",
        "image": "",
        "screenshots": [],
        "sourceType": "dealseek",
        "brand": "",
        "asin": ""
    }

    # 1. Parse dealHash from URL query parameter
    try:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        deal_hash = query_params.get("dealHash", [""])[0]

        if deal_hash:
            parts = deal_hash.split("-")
            if parts:
                # Part 0 is ASIN (10 chars, alphanumeric)
                asin = parts[0] if len(parts[0]) == 10 and parts[0].isalnum() else ""
                data["asin"] = asin
                if asin:
                    data["targetUrl"] = f"https://www.amazon.com/dp/{asin}"

                # Part 1 is merchant/seller ID
                seller_id = parts[1] if len(parts) > 1 and len(parts[1]) in (13, 14) and parts[1].isalnum() else ""
                if seller_id and data["targetUrl"]:
                    data["targetUrl"] += f"?m={seller_id}"

                # Part 2 is original price
                if len(parts) > 2 and parts[2]:
                    orig_p = parts[2]
                    data["originalPrice"] = f"${orig_p}" if not orig_p.startswith("$") else orig_p

                # Part 3 is sale price
                if len(parts) > 3 and parts[3]:
                    sale_p = parts[3]
                    data["salePrice"] = f"${sale_p}" if not sale_p.startswith("$") else sale_p

                # Search subsequent parts for the coupon code
                # Usually alphanumeric uppercase code, not purely numeric (since numeric is timestamp/etc)
                for p in parts[4:]:
                    if p and p.isalnum() and p.isupper() and 4 <= len(p) <= 20:
                        if not p.isdigit() and not p.startswith("B0"):
                            data["couponCode"] = p
                            break

                # Calculate discount percentage if we have prices
                if data["originalPrice"] and data["salePrice"]:
                    try:
                        orig_val = float(data["originalPrice"].replace("$", ""))
                        sale_val = float(data["salePrice"].replace("$", ""))
                        if orig_val > 0:
                            pct = round((orig_val - sale_val) / orig_val * 100)
                            data["discount"] = f"{pct}% OFF"
                    except Exception:
                        pass

                print(f"[Dealseek Crawler] Extracted from URL dealHash: asin={data['asin']}, code={data['couponCode']}, discount={data['discount']}, targetUrl={data['targetUrl']}")

                # If we got the ASIN and coupon code, we can return early
                if data["asin"] and data["couponCode"]:
                    return data
    except Exception as e:
        print(f"[Dealseek Crawler] Error parsing URL dealHash: {e}")

    # 2. DOM/HTML fallback: scan HTML for dealHash or __next_f push scripts or regex patterns
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Look for dealHash in text or attributes
        hash_match = re.search(r"dealHash=([A-Z0-9.\-]+)", html_content)
        if hash_match:
            deal_hash = hash_match.group(1)
            parts = deal_hash.split("-")
            if parts:
                asin = parts[0] if len(parts[0]) == 10 and parts[0].isalnum() else ""
                if asin and not data["asin"]:
                    data["asin"] = asin
                    data["targetUrl"] = f"https://www.amazon.com/dp/{asin}"
                    seller_id = parts[1] if len(parts) > 1 and len(parts[1]) in (13, 14) and parts[1].isalnum() else ""
                    if seller_id:
                        data["targetUrl"] += f"?m={seller_id}"

                if len(parts) > 2 and parts[2] and not data["originalPrice"]:
                    orig_p = parts[2]
                    data["originalPrice"] = f"${orig_p}" if not orig_p.startswith("$") else orig_p
                if len(parts) > 3 and parts[3] and not data["salePrice"]:
                    sale_p = parts[3]
                    data["salePrice"] = f"${sale_p}" if not sale_p.startswith("$") else sale_p

                if not data["couponCode"]:
                    for p in parts[4:]:
                        if p and p.isalnum() and p.isupper() and 4 <= len(p) <= 20:
                            if not p.isdigit() and not p.startswith("B0"):
                                data["couponCode"] = p
                                break

                if data["originalPrice"] and data["salePrice"] and not data["discount"]:
                    try:
                        orig_val = float(data["originalPrice"].replace("$", ""))
                        sale_val = float(data["salePrice"].replace("$", ""))
                        if orig_val > 0:
                            pct = round((orig_val - sale_val) / orig_val * 100)
                            data["discount"] = f"{pct}% OFF"
                    except Exception:
                        pass

        # Basic DOM element selectors (as generic fallbacks)
        if not data["couponCode"]:
            code_elem = soup.select_one(".promo-code, .coupon-code, .copy-code, [class*='code']")
            if code_elem:
                data["couponCode"] = code_elem.text.strip()

        if not data["originalPrice"]:
            orig_elem = soup.select_one(".original-price, [class*='originalPrice'], [class*='wasPrice']")
            if orig_elem:
                data["originalPrice"] = orig_elem.text.strip()

        if not data["salePrice"]:
            sale_elem = soup.select_one(".sale-price, [class*='salePrice'], [class*='nowPrice']")
            if sale_elem:
                data["salePrice"] = sale_elem.text.strip()

    return data


def extract_affitfy_data(html_content: str, url: str) -> dict:
    """
    Parses affitfy.com deal page HTML and extracts coupon details & Amazon target URL.
    Uses Affitfy REST API (https://api.affitfy.com/v1/deals/slug/{slug}) for fast,
    accurate extraction of the exact deal specified in the URL, with HTML parsing as fallback.
    """
    import urllib.parse
    import urllib.request
    import json
    data = {
        "isCoupon": True,
        "couponCode": "",
        "discount": "",
        "originalPrice": "",
        "salePrice": "",
        "targetUrl": "",
        "title": "",
        "description": "",
        "image": "",
        "screenshots": [],
        "sourceType": "affitfy",
        "brand": "",
        "asin": ""
    }

    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    deal_slug = query_params.get("deal", [""])[0]

    # 1. Try direct REST API fetch first if deal_slug is present in URL
    if deal_slug:
        api_url = f"https://api.affitfy.com/v1/deals/slug/{deal_slug}"
        try:
            req_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*'
            }
            req = urllib.request.Request(api_url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    api_data = json.loads(resp.read().decode('utf-8'))
                    if isinstance(api_data, dict):
                        deal_info = api_data.get("data") if isinstance(api_data.get("data"), dict) else api_data

                        # ASIN
                        asin = deal_info.get("asin") or deal_info.get("externalId") or ""
                        if asin:
                            data["asin"] = asin
                            data["targetUrl"] = f"https://www.amazon.com/dp/{asin}"

                        # Title
                        data["title"] = deal_info.get("dealTitle") or deal_info.get("title") or ""

                        # Coupon Code
                        promos = deal_info.get("promotions", [])
                        if isinstance(promos, list) and len(promos) > 0 and isinstance(promos[0], dict):
                            data["couponCode"] = promos[0].get("code") or ""
                        if not data["couponCode"]:
                            data["couponCode"] = deal_info.get("code") or deal_info.get("promoCode") or ""

                        # Prices
                        lp = deal_info.get("listPrice") or deal_info.get("price")
                        if lp is not None:
                            data["originalPrice"] = f"${lp}" if isinstance(lp, (int, float)) or not str(lp).startswith('$') else str(lp)

                        fp = deal_info.get("finalPrice") or deal_info.get("currentPrice")
                        if fp is not None:
                            data["salePrice"] = f"${fp}" if isinstance(fp, (int, float)) or not str(fp).startswith('$') else str(fp)

                        # Discount
                        disc_pct = deal_info.get("totalDiscountPct") or deal_info.get("discountPercent")
                        if disc_pct is not None:
                            try:
                                data["discount"] = f"{round(float(disc_pct))}% OFF"
                            except Exception:
                                pass

                        # Image
                        img_url = deal_info.get("primaryImage")
                        if img_url:
                            data["image"] = img_url
                        else:
                            img_id = deal_info.get("primaryImageId")
                            if img_id:
                                data["image"] = f"https://m.media-amazon.com/images/I/{img_id}.jpg"

                        # Screenshots list
                        imgs_list = deal_info.get("images", [])
                        if isinstance(imgs_list, list) and len(imgs_list) > 0:
                            data["screenshots"] = [
                                img["imageUrl"] for img in imgs_list
                                if isinstance(img, dict) and img.get("imageUrl")
                            ]

                        print(f"[Affitfy Crawler API] Fetched deal '{deal_slug}' -> ASIN: {data['asin']}, code: {data['couponCode']}, discount: {data['discount']}, targetUrl: {data['targetUrl']}")
                        if data["asin"]:
                            return data
        except Exception as e:
            print(f"[Affitfy Crawler API] Direct API call error: {e}")

    # 2. Fallback to HTML chunk & DOM parsing if API fetch didn't return ASIN
    if html_content:
        # Extract short ID from slug if present (e.g. d51a0fc1)
        deal_id = deal_slug.split("-")[-1] if deal_slug and "-" in deal_slug else ""
        soup = BeautifulSoup(html_content, 'html.parser')
        target_block = ""

        if deal_slug or deal_id:
            for s in soup.find_all('script'):
                text = s.string or ""
                if not text:
                    continue
                if deal_slug and deal_slug in text:
                    pos = text.find(deal_slug)
                    target_block = text[max(0, pos - 500): min(len(text), pos + 2000)]
                    break
                elif deal_id and len(deal_id) >= 6 and deal_id in text:
                    pos = text.find(deal_id)
                    target_block = text[max(0, pos - 500): min(len(text), pos + 2000)]
                    break

        if target_block:
            target_block_clean = target_block.replace('\\"', '"').replace('\\\\', '\\')

            # ASIN
            if not data["asin"]:
                asin_m = re.search(r'"asin"\s*:\s*"([A-Z0-9]{10})"', target_block_clean) or re.search(r'"externalId"\s*:\s*"([A-Z0-9]{10})"', target_block_clean)
                if asin_m:
                    data["asin"] = asin_m.group(1)
                    data["targetUrl"] = f"https://www.amazon.com/dp/{data['asin']}"

            # Title
            if not data["title"]:
                title_m = re.search(r'"dealTitle"\s*:\s*"([^"]+)"', target_block_clean)
                if title_m:
                    try:
                        data["title"] = title_m.group(1).encode().decode('unicode_escape', errors='ignore')
                    except Exception:
                        data["title"] = title_m.group(1)

            # Code
            if not data["couponCode"]:
                code_m = re.search(r'"code"\s*:\s*"([A-Z0-9]{4,20})"', target_block_clean) or re.search(r'"promoCode"\s*:\s*"([A-Z0-9]{4,20})"', target_block_clean)
                if code_m and not code_m.group(1).startswith("B0"):
                    data["couponCode"] = code_m.group(1)

            # Prices
            if not data["originalPrice"]:
                list_p = re.search(r'"listPrice"\s*:\s*([0-9.]+)', target_block_clean)
                if list_p:
                    data["originalPrice"] = f"${list_p.group(1)}"

            if not data["salePrice"]:
                final_p = re.search(r'"finalPrice"\s*:\s*([0-9.]+)', target_block_clean) or re.search(r'"price"\s*:\s*([0-9.]+)', target_block_clean)
                if final_p:
                    data["salePrice"] = f"${final_p.group(1)}"

            if not data["discount"]:
                disc_m = re.search(r'"totalDiscountPct"\s*:\s*([0-9.]+)', target_block_clean)
                if disc_m:
                    val = float(disc_m.group(1))
                    data["discount"] = f"{round(val)}% OFF"

            if not data["image"]:
                img_m = re.search(r'"primaryImageId"\s*:\s*"([^"]+)"', target_block_clean)
                if img_m:
                    data["image"] = f"https://m.media-amazon.com/images/I/{img_m.group(1)}.jpg"

        # Check open modal elements in DOM
        modal = soup.select_one('section[role="dialog"], [role="dialog"], div[class*="z-[2100]"], div[class*="backdrop"]')
        if modal:
            modal_text = modal.text
            modal_html = str(modal)

            # ASIN inside modal
            if not data["asin"]:
                modal_asins = re.findall(r'\b(B0[A-Z0-9]{8})\b', modal_html)
                if modal_asins:
                    data["asin"] = modal_asins[0]
                    data["targetUrl"] = f"https://www.amazon.com/dp/{data['asin']}"

            # Target link inside modal
            if not data["targetUrl"]:
                for a in modal.find_all("a", href=True):
                    href = a["href"]
                    if "amazon.com" in href or "amzn.to" in href:
                        data["targetUrl"] = href
                        dp_m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', href)
                        if dp_m:
                            data["asin"] = dp_m.group(1)
                        break

            # Code inside modal
            if not data["couponCode"]:
                code_match = re.search(r'\bCopy code\s+([A-Z0-9]{4,20})\b', modal_text, re.I)
                if not code_match:
                    code_match = re.search(r'\b(?:code|coupon)\s*[:\-]?\s*([A-Z0-9]{4,20})\b', modal_text, re.I)
                if code_match and not code_match.group(1).startswith("B0"):
                    data["couponCode"] = code_match.group(1).upper()

            # Title inside modal
            if not data["title"]:
                h_tag = modal.find(['h1', 'h2', 'h3'])
                if h_tag:
                    data["title"] = h_tag.text.strip()

    # Calculate discount percentage if missing
    if not data["discount"] and data["originalPrice"] and data["salePrice"]:
        try:
            o = float(data["originalPrice"].replace("$", ""))
            s = float(data["salePrice"].replace("$", ""))
            if o > 0:
                data["discount"] = f"{round((o - s) / o * 100)}% OFF"
        except Exception:
            pass

    print(f"[Affitfy Crawler Fallback] Extracted: asin={data['asin']}, code={data['couponCode']}, discount={data['discount']}, targetUrl={data['targetUrl']}")
    return data
