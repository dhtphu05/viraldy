import re
from bs4 import BeautifulSoup

def _normalize_image_url(url):
    if not url:
        return None
    url = url.strip().replace('\\/', '/')
    if not url.startswith('http'):
        return None
    url = re.sub(r'\._[^.]+\.(jpg|jpeg|png|gif|webp)$', r'.\1', url, flags=re.I)
    url = re.sub(r'(\.(?:jpg|jpeg|png|gif|webp))(?:\?.*)$', r'\1', url, flags=re.I)
    return url

def _unique_keep_order(values):
    seen = set()
    out = []
    for value in values:
        normalized = _normalize_image_url(value) if isinstance(value, str) else value
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out

def _extract_amazon_review_image_urls(html_content, soup):
    """
    Extract images that belong to Amazon customer reviews.
    This catches both visible DOM nodes and raw HTML references that appear
    in review carousels / lightboxes.
    """
    review_images = []

    # Visible image widgets commonly used in Amazon review sections
    selectors = [
        '#cr-lighthouse-image-media-link img',
        '.cr-lightbox-image-thumbnail img',
        '[data-hook="review-image-gallery"] img',
        '.review-image-tile img',
        '.review-image-container img',
        '[data-hook="review-image"] img',
        'img.review-image',
        'img[data-a-hires]',
        'img[data-old-hires]',
    ]
    for selector in selectors:
        for img in soup.select(selector):
            src = img.get('src') or img.get('data-src') or img.get('data-old-hires') or img.get('data-a-hires')
            normalized = _normalize_image_url(src)
            if normalized:
                review_images.append(normalized)

    # Raw HTML fallback for community review images
    patterns = [
        r'https://m\.media-amazon\.com/images/I/[^"\']+?(?:aicid=community-reviews|community-reviews|review)[^"\']*',
        r'https://images-na\.ssl-images-amazon\.com/images/I/[^"\']+?(?:aicid=community-reviews|community-reviews|review)[^"\']*',
    ]
    for pattern in patterns:
        for match in re.findall(pattern, html_content, flags=re.I):
            normalized = _normalize_image_url(match)
            if normalized:
                review_images.append(normalized)

    # Another fallback: look for any review-related image URLs in raw HTML
    for match in re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)(?:\?[^"\']*)?', html_content, flags=re.I):
        lower = match.lower()
        if any(token in lower for token in ('community-reviews', 'customer-reviews', 'review-image', 'cr-lighthouse', 'aicid=community-reviews')):
            normalized = _normalize_image_url(match)
            if normalized:
                review_images.append(normalized)

    return _unique_keep_order(review_images)

def parse_amazon_product(html_content, url):
    """
    Parses Amazon product detail page HTML and returns structured data.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}

    # 1. URL
    data['url'] = url

    # 2. ASIN
    asin_match = re.search(r'(?:/dp/|/gp/product/|/d/)([A-Z0-9]{10})', url)
    asin = asin_match.group(1) if asin_match else None
    if not asin:
        asin_elem = soup.find('input', {'id': 'ASIN'}) or soup.find('input', {'name': 'ASIN'})
        if asin_elem:
            asin = asin_elem.get('value', '').strip()
    data['asin'] = asin or "N/A"

    # Parent ASIN: shared by every color/size variant of one product. Lets the
    # batch pipeline detect that two rows are the same product and reuse the
    # generated videos instead of rendering duplicates.
    parent_match = re.search(r'"parentAsin"\s*:\s*"([A-Z0-9]{10})"', html_content)
    if not parent_match:
        parent_match = re.search(r'data-parent-asin="([A-Z0-9]{10})"', html_content)
    data['parent_asin'] = parent_match.group(1) if parent_match else ""

    # 3. Title (Tiêu đề)
    title_elem = soup.find(id='productTitle')
    data['title'] = title_elem.text.strip() if title_elem else "N/A"

    # 4. Brand (Thương hiệu)
    brand = "N/A"
    brand_elem = soup.find(id='bylineInfo') or soup.find(id='brand')
    if brand_elem:
        brand = brand_elem.text.strip()
        brand = re.sub(r'^(Visit the|Brand:)\s+', '', brand, flags=re.IGNORECASE)
        brand = re.sub(r'\s+Store$', '', brand, flags=re.IGNORECASE)
    else:
        brand_po = soup.select_one('.po-brand td.po-value') or soup.select_one('.po-brand .a-span9')
        if brand_po:
            brand = brand_po.text.strip()
    data['brand'] = brand

    # 5. Category (Danh mục)
    categories = []
    cat_container = soup.find(id='wayfinding-breadcrumbs_container') or soup.find(id='showing-breadcrumbs_div')
    if cat_container:
        cat_links = cat_container.find_all('a')
        categories = [link.text.strip() for link in cat_links if link.text.strip()]
    if not categories:
        # Fallback to .a-breadcrumb elements
        bread_list = soup.select(".a-breadcrumb li a")
        if not bread_list:
            bread_list = soup.select(".a-breadcrumb a")
        categories = [a.text.strip() for a in bread_list if a.text.strip()]

    data['categories'] = " > ".join(categories) if categories else "N/A"

    # 6. Price (Giá gốc / Khuyến mãi)
    price_original = "N/A"
    price_discount = "N/A"

    # Discounted price (Price to pay)
    price_to_pay = (
        soup.select_one('.priceToPay .a-offscreen') or
        soup.select_one('#corePrice_feature_div .a-offscreen') or
        soup.select_one('#corePriceDisplay_desktop_feature_div .a-offscreen') or
        soup.select_one('.apex-pricetopay-value .a-offscreen')
    )
    if price_to_pay:
        price_discount = price_to_pay.text.strip()
    else:
        a_price = soup.select_one('.a-price')
        if a_price:
            offscreen = a_price.select_one('.a-offscreen')
            if offscreen:
                price_discount = offscreen.text.strip()

    # Original Price
    basis_price = soup.select_one('.basisPrice .a-offscreen') or soup.select_one('.a-price.a-text-price .a-offscreen')
    if basis_price:
        price_original = basis_price.text.strip()

    if price_discount == "N/A":
        price_our = soup.find(id='priceblock_ourprice') or soup.find(id='priceblock_dealprice')
        if price_our:
            price_discount = price_our.text.strip()

    if price_original == "N/A" and price_discount != "N/A":
        price_original = price_discount

    data['price'] = {
        'original': price_original,
        'discounted': price_discount
    }

    # 7. Inventory (Tồn kho)
    inventory = "N/A"
    avail_elem = soup.find(id='availability')
    if avail_elem:
        inventory = avail_elem.text.strip()
        inventory = re.sub(r'\s+', ' ', inventory)
    data['inventory'] = inventory

    # 8. Images (Ảnh)
    images = []

    def get_base_img_url(url):
        # Strip all Amazon size modifiers like ._AC_SR38,50_ or ._AC_SX679_
        if not url: return None
        return re.sub(r'\._.*?_\.(jpg|jpeg|png|gif)$', r'.\1', url)

    # First, try to get all hiRes and large images from the raw HTML using regex
    # Amazon often embeds the full image gallery inside script tags as JSON strings
    hires = re.findall(r'hiRes[\"\']?\s*:\s*[\"\']([^\"\']+)[\"\']', html_content)
    large = re.findall(r'large[\"\']?\s*:\s*[\"\']([^\"\']+)[\"\']', html_content)

    for url in hires + large:
        base = get_base_img_url(url)
        if base and base not in images and "m.media-amazon.com" in base:
            images.append(base)

    # Fallback to DOM elements
    alt_images = soup.select('#altImages ul li img')
    for img in alt_images:
        src = img.get('src')
        if src and not src.endswith('.gif') and 'play-button' not in src:
            src_clean = get_base_img_url(src)
            if src_clean and src_clean not in images:
                images.append(src_clean)

    landing_img = soup.find(id='landingImage')
    if landing_img:
        # data-a-dynamic-image contains a JSON of high-res images
        dynamic_images = landing_img.get('data-a-dynamic-image')
        if dynamic_images:
            try:
                import json
                img_dict = json.loads(dynamic_images)
                for img_url in img_dict.keys():
                    base_url = get_base_img_url(img_url)
                    if base_url and base_url not in images:
                        images.insert(0, base_url)
            except Exception:
                pass

        # Fallback to src
        main_src = landing_img.get('src')
        if main_src:
            base_main = get_base_img_url(main_src)
            if base_main and base_main not in images:
                images.insert(0, base_main)

    data['images'] = images[:15]

    # 9. Videos (Video) – comprehensive extraction
    videos = []
    seen_videos = set()

    def _add_video(url: str) -> None:
        """Add a video URL if it's a real HTTP(S) .mp4 and not a duplicate."""
        if not url or not isinstance(url, str):
            return
        url = url.replace('\\/', '/').strip()
        # Skip blob: URLs – they are ephemeral browser-only references
        if url.startswith('blob:'):
            return
        # Must be a real downloadable URL
        if not url.startswith(('http://', 'https://')):
            return
        # Normalise – remove query params for dedup
        dedup_key = url.split('?')[0].lower()
        if dedup_key in seen_videos:
            return
        seen_videos.add(dedup_key)
        videos.append(url)

    # ── Source 1: Scan ALL <script> tags for .mp4 URLs ──
    # Amazon embeds video URLs in many different JS variables:
    #   colorImages, videoObjectJSON, immersive-view, riveted, etc.
    all_scripts = soup.find_all('script')
    for script in all_scripts:
        text = script.string or ''
        if not text:
            continue
        # Find all .mp4 or .m3u8 URLs in any script block
        mp4_urls = re.findall(
            r'(?:\"url\"|\"videoUrl\"|\"src\"|\"hlsUrl\"|\"dashUrl\"|\"mp4Url\"|\"fallbackUrl\"|\"lowUrl\"|\"highUrl\")'
            r'\s*:\s*"(https?://[^"]+\.(?:mp4|m3u8)[^"]*)"',
            text
        )
        for u in mp4_urls:
            _add_video(u)

        # Broader pattern: any HTTPS .mp4 or .m3u8 URL in scripts
        broad_mp4 = re.findall(
            r'(https?://[a-zA-Z0-9._/~:@!$&\'()*+,;=%-]+\.(?:mp4|m3u8)(?:/[a-zA-Z0-9._/%-]*)?)',
            text
        )
        for u in broad_mp4:
            _add_video(u)

    # ── Source 2: data-video-url and similar attributes ──
    for elem in soup.find_all(attrs={'data-video-url': True}):
        _add_video(elem['data-video-url'])
    for elem in soup.find_all(attrs={'data-src': True}):
        src = elem['data-src']
        if '.mp4' in src or '.m3u8' in src:
            _add_video(src)

    # ── Source 3: <video> and <source> tags ──
    for v_tag in soup.find_all('video'):
        src = v_tag.get('src')
        if src:
            _add_video(src)
        # Also check <source> children
        for source_tag in v_tag.find_all('source'):
            _add_video(source_tag.get('src', ''))

    # ── Source 4: JSON-LD structured data ──
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            import json
            ld_data = json.loads(script.string or '{}')
            items = ld_data if isinstance(ld_data, list) else [ld_data]
            for item in items:
                if isinstance(item, dict):
                    for key in ('video', 'contentUrl', 'embedUrl', 'thumbnailUrl'):
                        val = item.get(key)
                        if isinstance(val, str) and ('.mp4' in val or '.m3u8' in val):
                            _add_video(val)
                        elif isinstance(val, list):
                            for v in val:
                                if isinstance(v, str) and ('.mp4' in v or '.m3u8' in v):
                                    _add_video(v)
                                elif isinstance(v, dict):
                                    _add_video(v.get('contentUrl', ''))
                                    _add_video(v.get('embedUrl', ''))
        except (json.JSONDecodeError, TypeError):
            pass

    # ── Source 5: Elements with class/id containing "video" ──
    video_containers = soup.select(
        '[id*="video" i] a[href*=".mp4"], [id*="video" i] a[href*=".m3u8"], '
        '[class*="video" i] a[href*=".mp4"], [class*="video" i] a[href*=".m3u8"], '
        '[data-csa-c-type="widget"][data-csa-c-slot-id*="video" i]'
    )
    for elem in video_containers:
        href = elem.get('href', '')
        if '.mp4' in href or '.m3u8' in href:
            _add_video(href)

    # ── Source 6: Alt-images section video thumbnails → try to resolve ──
    # Amazon alt-images sometimes has video thumbnails with data attributes
    alt_video_thumbs = soup.select('#altImages li.videoThumbnail, #altImages li[data-csa-c-type="widget"]')
    for thumb in alt_video_thumbs:
        # Check for any data attribute containing a video URL
        for attr_name, attr_val in thumb.attrs.items():
            if isinstance(attr_val, str) and ('.mp4' in attr_val or '.m3u8' in attr_val):
                _add_video(attr_val)

    data['videos'] = videos

    # 10. Variants (Biến thể màu/size)
    variants = {}
    twister = soup.find(id='twister') or soup.find(id='twisterContainer')
    if twister:
        dimension_rows = twister.select('.a-row, .inline-twister-row')
        for row in dimension_rows:
            label_elem = row.select_one('.a-form-label, .inline-twister-dim-title')
            if label_elem:
                label_name = label_elem.text.strip().replace(':', '')
                val_elem = row.select_one('.selection, .inline-twister-dim-selected')
                current_val = val_elem.text.strip() if val_elem else ""

                options = []
                for li in row.select('li, .inline-twister-swatch'):
                    img = li.find('img')
                    opt_name = img.get('alt') if img else li.text.strip()
                    if not opt_name and li.get('data-default-asin'):
                        opt_name = li.get('data-default-asin')
                    if opt_name and opt_name not in options:
                        options.append(opt_name)

                variants[label_name] = {
                    'current': current_val,
                    'options': options
                }
    if not variants:
        # Fallback swatches parser
        color_variants = soup.select('#variation_color_name li img, .inline-twister-dim-color_name li img')
        if color_variants:
            variants['Color'] = {
                'options': list(set(img.get('alt') for img in color_variants if img.get('alt')))
            }
        size_variants = soup.select('#variation_size_name li span, .inline-twister-dim-size_name li span')
        if size_variants:
            variants['Size'] = {
                'options': list(set(span.text.strip() for span in size_variants if span.text.strip()))
            }
    data['variants'] = variants

    # 11. Description (Mô tả)
    desc_elem = soup.find(id='productDescription')
    data['description'] = desc_elem.text.strip() if desc_elem else "N/A"

    # 12. Bullet points (Mô tả chi tiết / Features)
    bullets = []
    bullet_div = soup.find(id='feature-bullets') or soup.find(id='featurebullets_feature_div')
    if bullet_div:
        items = bullet_div.select('ul li span.a-list-item')
        bullets = [item.text.strip() for item in items if item.text.strip()]
    data['bullet_points'] = bullets

    # 13. Specifications (Thông số kỹ thuật)
    specs = {}
    tech_tables = soup.select('#prodDetails table, #productDetails_techSpec_section_1 table')
    for table in tech_tables:
        rows = table.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.text.strip().replace('\u200e', '').replace('\u200f', '').replace(':', '')
                val = td.text.strip().replace('\u200e', '').replace('\u200f', '')
                specs[key] = val

    if not specs:
        detail_bullets = soup.select('#detailBullets_feature_div ul li')
        for li in detail_bullets:
            span = li.select('span.a-list-item')
            if span:
                parts = span[0].text.split(':')
                if len(parts) >= 2:
                    key = parts[0].strip().replace('\u200e', '').replace('\u200f', '').replace(':', '')
                    val = parts[1].strip().replace('\u200e', '').replace('\u200f', '')
                    specs[key] = val
    data['specifications'] = specs

    # 14. Ratings & Reviews (Đánh giá)
    rating = "N/A"
    review_count = "N/A"

    rating_elem = soup.select_one('#acrPopover') or soup.select_one('#averageCustomerReviews') or soup.select_one('.a-icon-star')
    if rating_elem:
        rating_text = rating_elem.get('title') or rating_elem.text.strip()
        rating_match = re.search(r'([0-9.]+)\s+out of', rating_text)
        if rating_match:
            rating = rating_match.group(1)

    review_elem = soup.select_one('#acrCustomerReviewText')
    if review_elem:
        review_text = review_elem.text.strip()
        review_match = re.search(r'([0-9,]+)', review_text)
        if review_match:
            review_count = review_match.group(1).replace(',', '')

    data['ratings'] = {
        'rating': rating,
        'reviews_count': review_count
    }

    # 15. Seller (Người bán)
    seller = "N/A"
    ships_from = "N/A"
    sold_by = "N/A"

    tabular_buybox = soup.select_one('#tabular-buybox') or soup.select_one('.tabular-buybox-container')
    if tabular_buybox:
        rows = tabular_buybox.select('.tabular-buybox-row')
        for row in rows:
            label = row.select_one('.tabular-buybox-label-text')
            value = row.select_one('.tabular-buybox-value-text')
            if label and value:
                lbl_text = label.text.strip().lower()
                val_text = value.text.strip()
                if 'ships from' in lbl_text:
                    ships_from = val_text
                elif 'sold by' in lbl_text:
                    sold_by = val_text

    merchant_info = soup.find(id='merchant-info')
    if merchant_info:
        merchant_text = merchant_info.text.strip()
        merchant_text_clean = re.sub(r'\s+', ' ', merchant_text)
        ships_match = re.search(r'ships\s+from\s+([^,and]+)', merchant_text_clean, re.I)
        sold_match = re.search(r'sold\s+by\s+([^,.]+)', merchant_text_clean, re.I)
        if ships_match and ships_from == "N/A":
            ships_from = ships_match.group(1).strip()
        if sold_match and sold_by == "N/A":
            sold_by = sold_match.group(1).strip()

        if "Fulfilled by Amazon" in merchant_text_clean:
            ships_from = "Amazon"
            if sold_by == "N/A":
                sold_by_match = re.search(r'Sold\s+by\s+(.*?)\s+and\s+Fulfilled', merchant_text_clean, re.I)
                if sold_by_match:
                    sold_by = sold_by_match.group(1).strip()

    seller_elem = soup.find(id='sellerProfileTriggerId')
    if seller_elem and sold_by == "N/A":
        sold_by = seller_elem.text.strip()

    data['seller_info'] = {
        'ships_from': ships_from,
        'sold_by': sold_by
    }

    # 16. Delivery Info (Thông tin giao hàng)
    delivery_info = "N/A"
    delivery_elem = soup.find(id='mir-layout-DELIVERY_BLOCK') or soup.find(id='deliveryBlockMessage') or soup.find(id='fastTrackMessage_feature_div')
    if delivery_elem:
        delivery_info = delivery_elem.text.strip()
        delivery_info = re.sub(r'\s+', ' ', delivery_info)
    data['delivery_info'] = delivery_info

    # 17. User Reviews (Đánh giá chi tiết của người dùng)
    reviews_list = []
    review_cards = []
    review_elements = soup.select('.review, [data-hook="review"]')
    for elem in review_elements:
        author_elem = elem.select_one('.a-profile-name, [data-hook="review-author"]')
        author = author_elem.text.strip() if author_elem else "Anonymous"

        rating_elem = (
            elem.select_one('[data-hook="review-star-rating"] span.a-icon-alt') or
            elem.select_one('i.review-rating span.a-icon-alt') or
            elem.select_one('.a-icon-star span.a-icon-alt')
        )
        rating_val = rating_elem.text.strip() if rating_elem else "N/A"
        rating_match = re.search(r'([0-9.]+)\s+out', rating_val)
        rating_val = rating_match.group(1) if rating_match else rating_val

        title_elem = (
            elem.select_one('[data-hook="reviewTitle"]') or
            elem.select_one('[data-hook="review-title"] span') or
            elem.select_one('.review-title-content span') or
            elem.select_one('[data-hook="review-title"]') or
            elem.select_one('h5[class*="review-title"]')
        )
        title_val = title_elem.text.strip() if title_elem else "N/A"
        title_val = re.sub(r'^[0-9.]+\s+out\s+of\s+5\s+stars\s*', '', title_val, flags=re.I)

        date_elem = elem.select_one('[data-hook="review-date"]')
        date_val = date_elem.text.strip() if date_elem else "N/A"

        body_elem = (
            elem.select_one('[data-hook="reviewRichContentContainer"]') or
            elem.select_one('[data-hook="review-body"] span') or
            elem.select_one('.review-text-content span') or
            elem.select_one('[data-hook="review-body"]') or
            elem.select_one('.review-text-content') or
            elem.select_one('div[class*="contain-rich-content"]')
        )
        body = body_elem.text.strip() if body_elem else "N/A"
        body = re.sub(r'\s+', ' ', body)

        # Avoid duplicates
        if body != "N/A" and not any(r['body'] == body for r in reviews_list):
            reviews_list.append({
                'author': author,
                'rating': rating_val,
                'title': title_val,
                'date': date_val,
                'body': body
            })

        review_image_urls = []
        for img in elem.select('.review-image-container img, [data-hook="review-image"] img, img.review-image, img[data-a-hires], img[data-old-hires]'):
            src = img.get('src') or img.get('data-src') or img.get('data-old-hires') or img.get('data-a-hires')
            if src:
                src_clean = get_base_img_url(src)
                if src_clean and src_clean not in review_image_urls:
                    review_image_urls.append(src_clean)

        if review_image_urls:
            review_cards.append({
                'author': author,
                'rating': rating_val,
                'title': title_val,
                'date': date_val,
                'body': body,
                'image_urls': review_image_urls[:5],
            })
        else:
            review_cards.append({
                'author': author,
                'rating': rating_val,
                'title': title_val,
                'date': date_val,
                'body': body,
                'image_urls': [],
            })
    data['reviews_list'] = reviews_list[:10]  # Get top 10 customer reviews

    buyer_images = []
    for elem in review_elements:
        for img in elem.select('.review-image-container img, [data-hook="review-image"] img, img.review-image'):
            src = img.get('src') or img.get('data-src') or img.get('data-old-hires')
            if src:
                src_clean = get_base_img_url(src)
                if src_clean and src_clean not in buyer_images:
                    buyer_images.append(src_clean)

    cr_media_container = soup.select('#cr-lighthouse-image-media-link img, .cr-lightbox-image-thumbnail img, [data-hook="review-image-gallery"] img, .review-image-tile img')
    for img in cr_media_container:
        src = img.get('src') or img.get('data-src') or img.get('data-old-hires')
        if src:
            src_clean = get_base_img_url(src)
            if src_clean and src_clean not in buyer_images:
                buyer_images.append(src_clean)

    raw_review_images = _extract_amazon_review_image_urls(html_content, soup)
    buyer_images = _unique_keep_order(buyer_images + raw_review_images)

    data['buyer_images'] = buyer_images[:15]
    data['review_images'] = buyer_images[:15]

    # Videos NOT made by the seller — influencer/customer clips. Amazon's
    # "Videos for this product" carousel tags every item with
    # data-creator-type (Seller / Influencer / Customer); anything non-Seller
    # is UGC-style footage the review video mode should prefer over brand
    # promo clips.
    review_videos = []

    def _collect_video_url(candidate):
        if not candidate:
            return
        candidate = candidate.replace('\\/', '/').strip()
        if candidate.startswith('http') and ('.mp4' in candidate or '.m3u8' in candidate):
            review_videos.append(candidate)

    for item in soup.select('.vse-video-item[data-video-url], [data-element-id="video-carousel-item"][data-video-url]'):
        creator = (item.get('data-creator-type') or '').strip().lower()
        if creator and creator != 'seller':
            _collect_video_url(item.get('data-video-url'))

    # Videos embedded inside individual review cards (customer uploads).
    for elem in review_elements:
        for v_tag in elem.select('video'):
            _collect_video_url(v_tag.get('src'))
            for s_tag in v_tag.select('source'):
                _collect_video_url(s_tag.get('src'))
        for holder in elem.select('[data-video-url]'):
            _collect_video_url(holder.get('data-video-url'))

    seen_rv = set()
    deduped_rv = []
    for v in review_videos:
        key = v.split('?')[0].lower()
        if key not in seen_rv:
            seen_rv.add(key)
            deduped_rv.append(v)
    data['review_videos'] = deduped_rv[:6]

    # "Customers say" AI summary. The heading string's direct parent is just
    # the heading node, which used to leak the literal text "Customers say"
    # into scripts. Target the summary widget first, then climb from the
    # heading to a container that holds real sentence text.
    customer_say_text = ""
    summary_widget = soup.select_one(
        '#product-summary p, [data-hook="cr-summarization-content"], '
        '#cr-product-insights-cards p, #cr-summarization-attributes'
    )
    if summary_widget:
        customer_say_text = summary_widget.get_text(" ", strip=True)
    if not customer_say_text:
        customer_say_elem = soup.find(string=re.compile(r'^\s*Customers say\s*$', re.I))
        if customer_say_elem:
            container = customer_say_elem.parent
            for _ in range(3):
                if container is None:
                    break
                text = container.get_text(" ", strip=True)
                text = re.sub(r'^\s*Customers say\s*', '', text, flags=re.I).strip()
                if len(text) > 40:
                    customer_say_text = text
                    break
                container = container.parent
    if not customer_say_text:
        customer_say_match = re.search(r'###\s*Customers say\s*(.+?)(?:\n#{1,6}\s|\Z)', html_content, re.I | re.S)
        if customer_say_match:
            customer_say_text = re.sub(r'\s+', ' ', customer_say_match.group(1)).strip()
    # A "summary" shorter than 40 chars is a leaked label/fragment, not a summary.
    if len(customer_say_text) <= 40 or re.fullmatch(r'customers say[.:]?', customer_say_text, re.I):
        customer_say_text = ""
    # Drop the boilerplate AI-disclaimer tail if present.
    customer_say_text = re.sub(r'\s*AI[- ]generated from the text of customer reviews.*$', '', customer_say_text, flags=re.I).strip()
    data['customer_say'] = customer_say_text

    data['review_cards'] = review_cards[:8]

    return data

def parse_amazon_listing(html_content, base_url):
    """
    Parses Amazon listing/search page HTML and extracts products.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []

    items = soup.select('[data-component-type="s-search-result"]')
    if not items:
        items = soup.select('.s-result-item[data-asin]')

    for item in items:
        asin = item.get('data-asin')
        if not asin or len(asin) != 10:
            continue

        title_elem = item.select_one('h2 a span') or item.select_one('h2 a')
        title = title_elem.text.strip() if title_elem else "N/A"

        url_elem = item.select_one('h2 a')
        url = ""
        if url_elem:
            href = url_elem.get('href', '')
            if href.startswith('http'):
                url = href
            else:
                url = "https://www.amazon.com" + href

        img_elem = item.select_one('img.s-image')
        image = img_elem.get('src') if img_elem else "N/A"

        price_elem = item.select_one('.a-price .a-offscreen')
        price = price_elem.text.strip() if price_elem else "N/A"

        rating_elem = item.select_one('.a-icon-star-small span.a-icon-alt') or item.select_one('.a-icon-star span.a-icon-alt')
        rating = rating_elem.text.strip() if rating_elem else "N/A"

        review_count_elem = item.select_one('a[href*="#customerReviews"] span.a-size-base') or item.select_one('.a-size-small a.a-link-normal span.a-size-base')
        review_count = review_count_elem.text.strip() if review_count_elem else "N/A"

        products.append({
            'asin': asin,
            'title': title,
            'url': url,
            'image': image,
            'price': price,
            'rating': rating,
            'reviews_count': review_count
        })
    return products

def generate_product_markdown(data):
    """
    Generates structured Markdown report for a product.
    """
    md = []
    md.append(f"# Product Details: {data['title']}\n")
    md.append(f"## General Information")
    md.append(f"- **ASIN**: `{data['asin']}`")
    md.append(f"- **URL**: [{data['url']}]({data['url']})")
    md.append(f"- **Brand**: {data['brand']}")
    md.append(f"- **Category**: {data['categories']}")
    md.append(f"- **Inventory**: {data['inventory']}")
    md.append(f"- **Ratings**: {data['ratings']['rating']} ⭐ ({data['ratings']['reviews_count']} reviews)")

    price_info = data['price']
    md.append(f"- **Price**:")
    md.append(f"  - Original Price: `{price_info['original']}`")
    md.append(f"  - Discounted/Current Price: `{price_info['discounted']}`")

    seller_info = data['seller_info']
    md.append(f"- **Seller & Delivery Info**:")
    md.append(f"  - Ships From: {seller_info['ships_from']}")
    md.append(f"  - Sold By: {seller_info['sold_by']}")
    md.append(f"  - Delivery Details: {data['delivery_info']}")

    md.append("\n## Introduce Images (Shop Uploaded Images)")
    if data['images']:
        for i, img in enumerate(data['images']):
            md.append(f"![Shop Image {i+1}]({img})")
    else:
        md.append("No shop images found.")

    md.append("\n## Review Images (Buyer Uploaded Images)")
    if data.get('buyer_images'):
        for i, img in enumerate(data['buyer_images']):
            md.append(f"![Buyer Image {i+1}]({img})")
    else:
        md.append("No buyer images found.")

    if data.get('customer_say'):
        md.append("\n## Customers say")
        md.append(data['customer_say'])

    if data.get('review_cards'):
        md.append("\n## Selected Review Cards")
        for i, rev in enumerate(data['review_cards']):
            md.append(f"### Review Card {i+1}")
            md.append(f"- **Author**: {rev.get('author', 'N/A')}")
            md.append(f"- **Rating**: {rev.get('rating', 'N/A')} ⭐")
            md.append(f"- **Title**: {rev.get('title', 'N/A')}")
            md.append(f"- **Date**: {rev.get('date', 'N/A')}")
            md.append(f"- **Body**: {rev.get('body', 'N/A')}")
            if rev.get('image_urls'):
                md.append(f"- **Images**: {', '.join(rev.get('image_urls', []))}")

    md.append("\n## Videos")
    if data['videos']:
        for i, vid in enumerate(data['videos']):
            md.append(f"- [Video {i+1}]({vid})")
    else:
        md.append("No videos found.")

    md.append("\n## Variants")
    if data['variants']:
        for label, info in data['variants'].items():
            current = info.get('current', '')
            options = ", ".join(info.get('options', []))
            md.append(f"- **{label}**: Current: `{current}` | Options: `[{options}]`")
    else:
        md.append("No variants found.")

    md.append("\n## Features (Bullet Points)")
    for bullet in data['bullet_points']:
        md.append(f"- {bullet}")

    md.append("\n## Specifications")
    if data['specifications']:
        md.append("| Technical Property | Detail Specification |")
        md.append("| --- | --- |")
        for key, val in data['specifications'].items():
            md.append(f"| {key} | {val} |")
    else:
        md.append("No technical specifications found.")

    md.append("\n## Customer Reviews (Đánh giá từ người dùng)")
    if data.get('reviews_list'):
        for i, rev in enumerate(data['reviews_list']):
            md.append(f"### Review {i+1}: {rev['title']}")
            md.append(f"- **Author**: {rev['author']}")
            md.append(f"- **Rating**: {rev['rating']} ⭐")
            md.append(f"- **Date**: {rev['date']}")
            md.append(f"- **Content**:\n  {rev['body']}\n")
    else:
        md.append("No user reviews found on this page.")

    md.append("\n## Description")
    md.append(data['description'])

    return "\n".join(md)

def generate_listing_markdown(products, search_url):
    """
    Generates structured Markdown report for a search/listing page.
    """
    md = []
    md.append(f"# Amazon Listing Results\n")
    md.append(f"- **Search/Listing URL**: {search_url}")
    md.append(f"- **Total Products Found**: {len(products)}")
    md.append("\n## Products Table\n")

    md.append("| Image | Title | ASIN | Price | Rating | Link |")
    md.append("| --- | --- | --- | --- | --- | --- |")
    for prod in products:
        img_md = f"![Product Image]({prod['image']})" if prod['image'] != "N/A" else "N/A"
        title_trunc = prod['title'][:80] + "..." if len(prod['title']) > 80 else prod['title']
        md.append(f"| {img_md} | {title_trunc} | `{prod['asin']}` | {prod['price']} | {prod['rating']} ({prod['reviews_count']}) | [View Product]({prod['url']}) |")

    return "\n".join(md)
