from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from fastapi import HTTPException
from pydantic import BaseModel

from viraldy.modules.product_import.security import (
    open_public_url,
    validate_public_http_url,
)
from viraldy.modules.product_import.vendor.aveflow.amazon import (
    generate_listing_markdown,
    generate_product_markdown,
    parse_amazon_listing,
    parse_amazon_product,
)
from viraldy.modules.product_import.vendor.aveflow.coupon_context import (
    extract_coupon_context,
)
from viraldy.shared.errors.base import AppError

PUBLIC_BASE_URL = os.environ.get(
    "PRODUCT_CRAWL_PUBLIC_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")
RENDERS_DIR = Path(
    os.environ.get(
        "PRODUCT_CRAWL_OUTPUT_DIR",
        str(Path(tempfile.gettempdir()) / "viraldy-product-crawl"),
    )
).resolve()
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

SCRAPE_MAX_CONCURRENCY = max(
    1,
    int(os.environ.get("PRODUCT_CRAWL_MAX_CONCURRENCY", "2")),
)
_scrape_semaphore = threading.Semaphore(SCRAPE_MAX_CONCURRENCY)

class CrawlRequest(BaseModel):
    url: str


# Markers that identify an Amazon bot-check / captcha / error interstitial.
# Any of these means the HTML is NOT a real product page and must not be
# parsed into product data (a blocked page previously produced title "N/A"
# and leaked unrelated promo videos into the render pipeline).
AMAZON_BLOCK_MARKERS = (
    "api-services-support@amazon.com",
    "to discuss automated access to amazon data",
    "enter the characters you see below",
    "type the characters you see in this image",
    "validatecaptcha",
    "sorry, we just need to make sure you're not a robot",
)


def amazon_product_page_blocked(html: str) -> bool:
    """True when an Amazon /dp/ crawl returned a bot-check or broken page."""
    if not html:
        return True
    lower = html.lower()
    if any(marker in lower for marker in AMAZON_BLOCK_MARKERS):
        return True
    # A real product detail page always carries the productTitle node.
    return 'id="producttitle"' not in lower

async def _scrape_url(req: CrawlRequest):
    url = req.url
    print(f"[Crawl Started] Target URL: {url}")

    url_lower_early = url.lower()
    is_amazon_target = "amazon.com" in url_lower_early

    # Configure Browser Options.
    # For Amazon: stealth mode + a real desktop UA + US locale cookies. The
    # default headless fingerprint gets served bot-check pages (title "N/A")
    # and geo-localized variants (VND prices, missing review section).
    amazon_cookies = [
        {"name": "i18n-prefs", "value": "USD", "domain": ".amazon.com", "path": "/"},
        {"name": "lc-main", "value": "en_US", "domain": ".amazon.com", "path": "/"},
    ]
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
        enable_stealth=True,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        headers={"Accept-Language": "en-US,en;q=0.9"},
        cookies=amazon_cookies if is_amazon_target else [],
    )

    # JS Injection: scroll page progressively, trigger lazy-loaded images, click video thumbnails, and play videos
    js_click_video = """
    // 1. Progressive scroll to trigger IntersectionObserver-based lazy loaders
    const scrollStep = Math.max(300, window.innerHeight);
    const maxScroll = document.body.scrollHeight;
    for (let y = 0; y < maxScroll; y += scrollStep) {
        window.scrollTo(0, y);
        await new Promise(r => setTimeout(r, 300));
    }
    window.scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 500));

    // 2. Force lazy-loaded images: convert data-src, data-lazy-src, data-original to src
    document.querySelectorAll('img[data-src], img[data-lazy-src], img[data-original], img[data-srcset]').forEach(img => {
        const lazySrc = img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.getAttribute('data-original');
        if (lazySrc) img.setAttribute('src', lazySrc);
        const lazySrcset = img.getAttribute('data-srcset');
        if (lazySrcset) img.setAttribute('srcset', lazySrcset);
    });

    // 3. Force lazy-loaded videos: convert data-src on video/source elements
    document.querySelectorAll('video[data-src], video source[data-src]').forEach(el => {
        const lazySrc = el.getAttribute('data-src');
        if (lazySrc) el.setAttribute('src', lazySrc);
    });

    // 4. Click Amazon video thumbnails to trigger lazy-loaded video playback
    const videoThumbs = document.querySelectorAll('#altImages li.videoThumbnail input, #altImages li.videoThumbnail, .video-thumbnail, [data-video-url]');
    videoThumbs.forEach(thumb => {
        try { thumb.click(); } catch (e) {}
    });
    await new Promise(r => setTimeout(r, 2500));

    // 5. Trigger muted playback on all discovered <video> elements to force media stream requests
    document.querySelectorAll('video').forEach(v => {
        try {
            v.muted = true;
            v.play().catch(() => {});
        } catch (e) {}
    });
    await new Promise(r => setTimeout(r, 1500));

    // 6. Make sure the customer-review section is loaded before returning HTML.
    // Amazon injects the whole review widget lazily via AJAX (on some variants
    // even its container is absent at first paint), so poll unconditionally
    // while nudging the scroll position; without this the crawl reports
    // "no customer reviews" even though the product has them.
    if (document.getElementById('productTitle')) {
        window.scrollTo(0, document.body.scrollHeight);
        for (let i = 0; i < 30; i++) {
            if (document.querySelector('[data-hook="review"], #cm-cr-dp-review-list, .review')) break;
            window.scrollBy(0, -300);
            window.scrollBy(0, 300);
            await new Promise(r => setTimeout(r, 500));
        }
        const reviewAnchor = document.querySelector('#reviewsMedley, #cm-cr-dp-review-list, [data-hook="reviews-medley-footer"], #customerReviews');
        if (reviewAnchor) {
            reviewAnchor.scrollIntoView({ block: 'center' });
            await new Promise(r => setTimeout(r, 800));
        }
    }
    """

    # Configure Run Options
    run_config = CrawlerRunConfig(
        scan_full_page=True,        # Automatically scrolls to the bottom of the page
        wait_for_images=True,       # Ensures lazy-loaded images are fully rendered
        delay_before_return_html=2.0, # Extra wait for pending AJAX/network requests
        js_code=js_click_video,     # Execute custom JS to simulate user interactions
        cache_mode=CacheMode.BYPASS # Always request fresh content
    )

    intercepted_videos = set()
    safe_hosts: set[str] = set()

    async def enforce_safe_request(route) -> None:
        request_url = route.request.url
        parsed_request = urlsplit(request_url)
        if parsed_request.scheme not in {"http", "https"}:
            if parsed_request.scheme in {"about", "blob", "data"}:
                await route.continue_()
            else:
                print(f"[Network Guard] Blocked non-HTTP request: {request_url[:120]}")
                await route.abort("blockedbyclient")
            return
        hostname = (parsed_request.hostname or "").lower()
        if hostname not in safe_hosts:
            try:
                await asyncio.to_thread(validate_public_http_url, request_url)
            except AppError:
                print(f"[Network Guard] Blocked unsafe request: {request_url[:120]}")
                await route.abort("blockedbyclient")
                return
            safe_hosts.add(hostname)
        await route.continue_()

    # Custom Playwright Hook for Network Interception (requests + responses)
    async def log_network_requests(page, context, **kwargs):
        print("\n[Network Hook] Setting up network request interception...")
        await page.route("**/*", enforce_safe_request)

        def on_request(request):
            req_url = request.url
            if ".mp4" in req_url or ".m3u8" in req_url or ".webm" in req_url or ".mov" in req_url:
                print(f"  -> [Network Intercept VIDEO REQUEST] {req_url[:90]}...")
                intercepted_videos.add(req_url)

        def on_response(response):
            content_type = response.headers.get("content-type", "")
            resp_url = response.url
            normalized_content_type = content_type.lower()
            if "mp2t" in normalized_content_type:
                return
            if "video/" in normalized_content_type or "mpegurl" in normalized_content_type:
                print(f"  -> [Network Intercept VIDEO RESPONSE] {resp_url[:90]}... (type: {content_type})")
                intercepted_videos.add(resp_url)

        page.on("request", on_request)
        page.on("response", on_response)
        return page

    coupon_data = None
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Register the network logging / interception hook
            crawler.crawler_strategy.set_hook("on_page_context_created", log_network_requests)

            url_lower = url.lower()
            is_koupon = "koupon.ai" in url_lower
            is_dealseek = "dealseek.com" in url_lower
            is_affitfy = "affitfy.com" in url_lower
            is_amazon = "amazon.com" in url_lower
            is_app_store = "apps.apple.com" in url_lower or "play.google.com" in url_lower

            if is_koupon:
                print("\n[Parsing] Detected Koupon.ai URL, crawling coupon first...")
                koupon_result = await crawler.arun(url=url, config=run_config)
                if not koupon_result.success:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to crawl Koupon.ai: {koupon_result.error_message}"
                    )
                from viraldy.modules.product_import.vendor.aveflow.coupon import (
                    extract_koupon_data,
                )
                coupon_data = extract_koupon_data(koupon_result.html, url)
                target_url = coupon_data.get("targetUrl")
                if target_url and ("amazon.com" in target_url or "/dp/" in target_url or "/gp/product/" in target_url):
                    print(f"[Koupon Crawler] Found Amazon target URL: {target_url}. Transitioning to Amazon crawl...")
                    url = target_url
                    url_lower = url.lower()
                    is_amazon = True
                else:
                    print("[Koupon Crawler] No Amazon target URL found or not an Amazon link. Returning Koupon data directly.")
                    return {
                        "title": coupon_data.get("title") or "Unknown Product",
                        "description": coupon_data.get("description") or "",
                        "image": coupon_data.get("image") or "",
                        "markdown": f"# Coupon Product: {coupon_data.get('title')}\nPromo Code: {coupon_data.get('couponCode')}\nDiscount: {coupon_data.get('discount')}\n",
                        "screenshots": coupon_data.get("screenshots") or [],
                        "videos": [],
                        "sourceType": "amazon",
                        "confidence": 0.8,
                        "reviews": [],
                        "rating": "N/A",
                        "reviews_count": "N/A",
                        "buyer_images": [],
                        "review_images": [],
                        "customer_say": "",
                        "review_cards": [],
                        "isCoupon": True,
                        "couponCode": coupon_data.get("couponCode"),
                        "discount": coupon_data.get("discount"),
                        "originalPrice": coupon_data.get("originalPrice"),
                        "salePrice": coupon_data.get("salePrice"),
                        "targetUrl": coupon_data.get("targetUrl") or url,
                    }

            elif is_dealseek:
                print("\n[Parsing] Detected Dealseek.com URL, parsing coupon details...")
                from viraldy.modules.product_import.vendor.aveflow.coupon import (
                    extract_dealseek_data,
                )
                # Extract dealseek data. Try URL first.
                coupon_data = extract_dealseek_data("", url)

                # If coupon_data doesn't have ASIN, crawl page as fallback
                if not coupon_data.get("asin") or not coupon_data.get("couponCode"):
                    print("[Dealseek Crawler] URL parse incomplete, crawling page as fallback...")
                    dealseek_result = await crawler.arun(url=url, config=run_config)
                    if dealseek_result.success:
                        coupon_data = extract_dealseek_data(dealseek_result.html, url)

                target_url = coupon_data.get("targetUrl")
                if target_url and ("amazon.com" in target_url or "/dp/" in target_url or "/gp/product/" in target_url):
                    print(f"[Dealseek Crawler] Found Amazon target URL: {target_url}. Transitioning to Amazon crawl...")
                    url = target_url
                    url_lower = url.lower()
                    is_amazon = True
                else:
                    print("[Dealseek Crawler] No Amazon target URL found or not an Amazon link. Returning Dealseek data directly.")
                    return {
                        "title": coupon_data.get("title") or "Unknown Product",
                        "description": coupon_data.get("description") or "",
                        "image": coupon_data.get("image") or "",
                        "markdown": f"# Coupon Product: {coupon_data.get('title')}\nPromo Code: {coupon_data.get('couponCode')}\nDiscount: {coupon_data.get('discount')}\n",
                        "screenshots": coupon_data.get("screenshots") or [],
                        "videos": [],
                        "sourceType": "amazon",
                        "confidence": 0.8,
                        "reviews": [],
                        "rating": "N/A",
                        "reviews_count": "N/A",
                        "buyer_images": [],
                        "review_images": [],
                        "customer_say": "",
                        "review_cards": [],
                        "isCoupon": True,
                        "couponCode": coupon_data.get("couponCode"),
                        "discount": coupon_data.get("discount"),
                        "originalPrice": coupon_data.get("originalPrice"),
                        "salePrice": coupon_data.get("salePrice"),
                        "targetUrl": coupon_data.get("targetUrl") or url,
                    }

            elif is_affitfy:
                print("\n[Parsing] Detected Affitfy.com URL, parsing coupon details...")
                from viraldy.modules.product_import.vendor.aveflow.coupon import (
                    extract_affitfy_data,
                )
                # Try direct REST API extraction first (fast & reliable)
                coupon_data = extract_affitfy_data("", url)

                # If API didn't return targetUrl, fallback to Playwright page crawl
                if not coupon_data.get("targetUrl"):
                    print("[Affitfy Crawler] API parse incomplete, crawling page as fallback...")
                    affitfy_result = await crawler.arun(url=url, config=run_config)
                    if affitfy_result.success:
                        coupon_data = extract_affitfy_data(affitfy_result.html, url)

                target_url = coupon_data.get("targetUrl")
                if target_url and ("amazon.com" in target_url or "/dp/" in target_url or "/gp/product/" in target_url):
                    print(f"[Affitfy Crawler] Found Amazon target URL: {target_url}. Transitioning to Amazon crawl...")
                    url = target_url
                    url_lower = url.lower()
                    is_amazon = True
                else:
                    print("[Affitfy Crawler] No Amazon target URL found or not an Amazon link. Returning Affitfy data directly.")
                    return {
                        "title": coupon_data.get("title") or "Unknown Product",
                        "description": coupon_data.get("description") or "",
                        "image": coupon_data.get("image") or "",
                        "markdown": f"# Coupon Product: {coupon_data.get('title')}\nPromo Code: {coupon_data.get('couponCode')}\nDiscount: {coupon_data.get('discount')}\n",
                        "screenshots": coupon_data.get("screenshots") or [],
                        "videos": [],
                        "sourceType": "amazon",
                        "confidence": 0.8,
                        "reviews": [],
                        "rating": "N/A",
                        "reviews_count": "N/A",
                        "buyer_images": [],
                        "review_images": [],
                        "customer_say": "",
                        "review_cards": [],
                        "isCoupon": True,
                        "couponCode": coupon_data.get("couponCode"),
                        "discount": coupon_data.get("discount"),
                        "originalPrice": coupon_data.get("originalPrice"),
                        "salePrice": coupon_data.get("salePrice"),
                        "targetUrl": coupon_data.get("targetUrl") or url,
                    }

            is_amazon_product = is_amazon and ("/dp/" in url or "/gp/product/" in url or "/d/" in url)

            # Run Crawl — Amazon product pages get retries because Amazon
            # intermittently serves bot-check pages (no product data) or a
            # variant whose review section did not load.
            max_attempts = 3 if is_amazon_product else 1
            result = None
            amazon_parsed = None
            best_intercepted = None  # network-intercepted videos from the attempt amazon_parsed came from
            for attempt in range(1, max_attempts + 1):
                # Videos intercepted from a blocked/interstitial page belong to
                # unrelated promos — never let them leak into the next attempt.
                intercepted_videos.clear()
                if attempt == 1:
                    result = await crawler.arun(url=url, config=run_config)
                else:
                    # Retry in a fresh browser context: once Amazon flags a
                    # session with a captcha, the same session tends to stay
                    # blocked, while a new context gets fresh session cookies.
                    async with AsyncWebCrawler(config=browser_config) as fresh_crawler:
                        fresh_crawler.crawler_strategy.set_hook("on_page_context_created", log_network_requests)
                        result = await fresh_crawler.arun(url=url, config=run_config)
                if not is_amazon_product:
                    break

                if amazon_product_page_blocked(result.html):
                    print(f"[Crawl Retry] Attempt {attempt}/{max_attempts}: Amazon bot-check/blocked page detected for {url}")
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                    continue

                candidate = parse_amazon_product(result.html, url)
                if candidate.get('title', 'N/A') in ('', 'N/A'):
                    print(f"[Crawl Retry] Attempt {attempt}/{max_attempts}: page rendered without a product title.")
                    if attempt < max_attempts:
                        await asyncio.sleep(2 * attempt)
                    continue
                reviews_count = str(candidate.get('ratings', {}).get('reviews_count', 'N/A'))
                reviews_expected = reviews_count not in ('N/A', '0', '')
                # Amazon serves a "Customer reviews require account
                # verification" sign-in prompt instead of review text to
                # logged-out sessions. That gate is deterministic — retrying
                # won't reveal reviews, so accept the page as-is.
                reviews_gated = 'cm-cr-dp-sign-in-prompt' in (result.html or '')
                if reviews_gated and reviews_expected and not candidate.get('reviews_list'):
                    print(f"[Crawl] {reviews_count} reviews are sign-in gated by Amazon — continuing with 'Customers say' summary and buyer media only.")
                if reviews_expected and not candidate.get('reviews_list') and not reviews_gated and attempt < max_attempts:
                    # Keep this parse as best-so-far, but retry once more to
                    # capture the lazy-loaded review section.
                    amazon_parsed = candidate
                    best_intercepted = set(intercepted_videos)
                    print(f"[Crawl Retry] Attempt {attempt}/{max_attempts}: product reports {reviews_count} reviews but none captured — retrying for reviews.")
                    await asyncio.sleep(2)
                    continue

                if reviews_expected and not candidate.get('reviews_list') and not reviews_gated:
                    # Final attempt still has no reviews and no sign-in gate.
                    # The page is otherwise healthy (title + review count
                    # parsed), so the review widget markup likely changed —
                    # dump the served HTML so the stale selectors can be
                    # diagnosed against it.
                    try:
                        import uuid as uuid_mod
                        debug_name = f"review-debug-{uuid_mod.uuid4().hex[:8]}.html"
                        (RENDERS_DIR / debug_name).write_text(result.html or "", encoding="utf-8")
                        print(f"[Crawl Debug] {reviews_count} reviews expected, none captured after {max_attempts} attempts — HTML saved: {PUBLIC_BASE_URL}/outputs/renders/{debug_name}")
                    except Exception as dump_err:
                        print(f"[Crawl Debug] HTML dump failed: {dump_err}")

                amazon_parsed = candidate
                best_intercepted = set(intercepted_videos)
                break

            if is_amazon_product and best_intercepted is not None:
                # A later (possibly blocked) attempt may have replaced the
                # intercepted set — restore the snapshot that matches the
                # parse we are actually returning.
                intercepted_videos.clear()
                intercepted_videos.update(best_intercepted)

            if is_amazon_product and amazon_parsed is None:
                raise HTTPException(
                    status_code=502,
                    detail="Amazon blocked the crawl (bot-check/captcha page) — no product data available. Re-run this URL later.",
                )

            title = "Unknown Product"
            description = ""
            image = ""
            md_content = ""
            screenshots = []
            videos = []
            rating = "N/A"
            buyer_images = []
            review_images = []
            customer_say = ""
            review_cards = []
            parsed_data = None

            if is_amazon:
                is_product = is_amazon_product
                if is_product:
                    print("\n[Parsing] Detected Amazon Product Detail Page...")
                    parsed_data = amazon_parsed
                    md_content = generate_product_markdown(parsed_data)
                    rating = parsed_data.get('ratings', {}).get('rating', 'N/A')
                    buyer_images = parsed_data.get('buyer_images', [])
                    review_images = parsed_data.get('review_images', [])
                    customer_say = parsed_data.get('customer_say', '')
                    review_cards = parsed_data.get('review_cards', [])
                else:
                    print("\n[Parsing] Detected Amazon Search/Listing Page...")
                    products = parse_amazon_listing(result.html, url)
                    md_content = generate_listing_markdown(products, url)
                    title = f"Amazon Search Results"
                    description = f"Found {len(products)} products"
                    if products and products[0].get('image'):
                        image = products[0]['image']
                    if products and products[0].get('videos'):
                        videos = products[0].get('videos', [])
                    if products:
                        screenshots = [p['image'] for p in products if p.get('image')]
                if is_product and parsed_data:
                    title = parsed_data.get('title', 'amazon_product')
                    description = parsed_data.get('description', '')
                    images = parsed_data.get('images', [])
                    videos = parsed_data.get('videos', [])
                    if images:
                        image = images[0]
                        screenshots = images

            elif is_app_store:
                print("\n[Parsing] Detected App Store / Google Play Page...")
                from viraldy.modules.product_import.vendor.aveflow.app_store import (
                    generate_app_markdown,
                    parse_app_store,
                )
                parsed_data = parse_app_store(result.html, url, result.media)
                md_content = generate_app_markdown(parsed_data)
                title = parsed_data.get('title', 'app_store_app')
                description = parsed_data.get('description', '')
                screenshots = parsed_data.get('screenshots', [])
                videos = parsed_data.get('videos', [])
                icon = parsed_data.get('icon', '')
                if icon and icon != 'N/A':
                    image = icon
                elif screenshots:
                    image = screenshots[0]

            else:
                print("\n[Parsing] Detected Generic Page...")
                md_content = result.markdown
                title = "Generic Web Page"
                description = ""

                # Extract media from crawl4ai's result.media
                if result.media and isinstance(result.media, dict):
                    images_data = result.media.get("images", [])
                    if images_data:
                        # Extract src and filter out empty ones
                        img_urls = [img.get("src") for img in images_data if isinstance(img, dict) and img.get("src")]
                        # Remove duplicates while preserving order
                        seen = set()
                        screenshots = [x for x in img_urls if not (x in seen or seen.add(x))]
                        if screenshots:
                            image = screenshots[0]

                    videos_data = result.media.get("videos", [])
                    if videos_data:
                        vid_urls = [v.get("src") for v in videos_data if isinstance(v, dict) and v.get("src")]
                        seen_vid = set()
                        videos = [x for x in vid_urls if not (x in seen_vid or seen_vid.add(x))]

            import urllib.parse
            if image:
                image = urllib.parse.urljoin(url, image)
            screenshots = [urllib.parse.urljoin(url, s) for s in screenshots if s]

            # Merge intercepted videos from the network hook
            if intercepted_videos:
                print(f"[Network] Merging {len(intercepted_videos)} intercepted videos into results")
                videos.extend(list(intercepted_videos))

            videos = [urllib.parse.urljoin(url, v) for v in videos if v]

            # Write to outputs/result.md ALWAYS
            result_md_path = RENDERS_DIR / "result.md"
            with open(result_md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"[SUCCESS] Saved crawl result to {result_md_path}")

            # Filter screenshots by dimensions - keep only quality images
            filtered_screenshots = []
            if screenshots:
                from PIL import Image as PILImage
                import io
                print(f"[Image Filter] Checking {len(screenshots)} images for quality...")
                for img_url in screenshots[:15]:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        req_img = urllib.request.Request(img_url, headers=headers)
                        with open_public_url(req_img, timeout=10) as response:
                            img_data = response.read()
                            img = PILImage.open(io.BytesIO(img_data))
                            width, height = img.size
                            aspect_ratio = width / max(height, 1)

                            # Keep images: width >= 300, height >= 300, reasonable aspect ratio (especially for mobile screenshots)
                            if width >= 300 and height >= 300 and 0.2 < aspect_ratio < 5.0:
                                filtered_screenshots.append(img_url)

                            if len(filtered_screenshots) >= 8:
                                break
                    except Exception as e:
                        print(f"[Image Filter] Skipped image: {str(e)[:50]}")
                        continue
                print(f"[Image Filter] Kept {len(filtered_screenshots)} quality images")
            # Resolve HLS (.m3u8) URLs to playable MP4 counterparts (especially for Amazon videos)
            def resolve_hls(v):
                if '.hls.m3u8' in v:
                    return v.replace('.hls.m3u8', '.mp4.480.mp4')
                if '.m3u8' in v:
                    return v.replace('.m3u8', '.mp4')
                return v

            resolved_videos = [resolve_hls(v) for v in videos]

            # Buyer/influencer review videos are HLS-only on Amazon (their
            # static .mp4 artifacts 404), and the renderer can only play
            # direct MP4s — so download the top clips to local MP4s with
            # ffmpeg (stream copy, fast) and serve them from RENDERS_DIR.
            review_videos = []
            if isinstance(parsed_data, dict) and parsed_data.get('review_videos'):
                import subprocess
                import time as time_mod
                import uuid as uuid_mod

                # Clips are only needed between scrape and render (minutes),
                # but nothing deleted them — a day of batch runs left 14GB of
                # orphans and filled the disk. Prune expired clips on every
                # scrape so the pool stays bounded without a separate cron.
                ttl_seconds = max(
                    1,
                    int(os.environ.get("PRODUCT_CRAWL_REVIEW_CLIP_TTL_HOURS", "6")),
                ) * 3600
                cutoff = time_mod.time() - ttl_seconds
                try:
                    pruned = 0
                    for stale in RENDERS_DIR.glob("review-clip-*.mp4"):
                        if stale.stat().st_mtime < cutoff:
                            stale.unlink(missing_ok=True)
                            pruned += 1
                    if pruned:
                        print(f"[Review Video] Pruned {pruned} review clips older than {ttl_seconds // 3600}h")
                except Exception as prune_err:
                    print(f"[Review Video] Prune failed: {str(prune_err)[:80]}")

                def _download_review_clip(src_url: str) -> str | None:
                    out_name = f"review-clip-{uuid_mod.uuid4().hex[:12]}.mp4"
                    out_path = RENDERS_DIR / out_name
                    try:
                        validate_public_http_url(src_url)
                        result_dl = subprocess.run(
                            [
                                'ffmpeg', '-y', '-v', 'error',
                                '-user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                                '-i', src_url,
                                '-t', '60',
                                '-c', 'copy', '-bsf:a', 'aac_adtstoasc',
                                str(out_path),
                            ],
                            capture_output=True, timeout=90,
                        )
                        if result_dl.returncode == 0 and out_path.exists() and out_path.stat().st_size > 100_000:
                            return f"{PUBLIC_BASE_URL}/outputs/renders/{out_name}"
                    except Exception as dl_err:
                        print(f"[Review Video] Download failed: {str(dl_err)[:80]}")
                    out_path.unlink(missing_ok=True)
                    return None

                for raw_rv in parsed_data.get('review_videos', [])[:3]:
                    downloaded = await asyncio.to_thread(_download_review_clip, raw_rv)
                    if downloaded:
                        review_videos.append(downloaded)
                if review_videos:
                    print(f"[Review Video] Downloaded {len(review_videos)} buyer/influencer clips to local MP4")

            # Filter and verify videos — keep only real reachable downloadable URLs
            import concurrent.futures

            def is_playable_video_response(v_url, content_type):
                normalized_content_type = (content_type or "").split(";")[0].strip().lower()
                if "mp2t" in normalized_content_type or "mpegurl" in normalized_content_type:
                    return False
                if normalized_content_type in ("video/mp4", "video/webm", "video/quicktime", "video/x-m4v"):
                    return True
                if normalized_content_type == "application/octet-stream":
                    return any(ext in v_url.lower() for ext in (".mp4", ".webm", ".mov", ".m4v"))
                return False

            def check_video_url(v_url):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    req_val = urllib.request.Request(v_url, headers=headers, method='HEAD')
                    with open_public_url(req_val, timeout=2.0) as resp:
                        if resp.status in (200, 206) and is_playable_video_response(v_url, resp.headers.get("content-type", "")):
                            return v_url
                except Exception:
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Range': 'bytes=0-100'
                        }
                        req_val = urllib.request.Request(v_url, headers=headers, method='GET')
                        with open_public_url(req_val, timeout=2.0) as resp:
                            if resp.status in (200, 206) and is_playable_video_response(v_url, resp.headers.get("content-type", "")):
                                return v_url
                    except Exception:
                        pass
                return None

            filtered_videos = []
            candidates = [
                v for v in resolved_videos
                if v and not v.startswith('blob:') and v.startswith(('http://', 'https://'))
            ]
            if candidates:
                print(f"[Video Filter] Verifying {len(candidates)} candidate videos for reachability...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    results = executor.map(check_video_url, candidates)
                    for res in results:
                        if res:
                            filtered_videos.append(res)
                print(f"[Video Filter] Kept {len(filtered_videos)} reachable videos out of {len(candidates)}")


            # Compute source type and confidence
            source_type = "unknown"
            if is_amazon:
                source_type = "amazon"
            elif is_app_store:
                source_type = "app_store"
            else:
                source_type = "website"

            # Simple confidence heuristic based on data completeness
            confidence = 0.5
            if title and title != "Unknown Product" and title != "Generic Web Page":
                confidence += 0.15
            if (filtered_screenshots or screenshots) and len(filtered_screenshots or screenshots) >= 2:
                confidence += 0.15
            if filtered_videos:
                confidence += 0.1
            if md_content and len(md_content) > 200:
                confidence += 0.1
            confidence = min(1.0, confidence)

            # Extract reviews if available
            reviews_list = []
            if isinstance(parsed_data, dict):
                reviews_list = parsed_data.get('reviews_list', [])
                review_images = parsed_data.get('review_images', review_images)
                customer_say = parsed_data.get('customer_say', customer_say)
                review_cards = parsed_data.get('review_cards', review_cards)

            coupon_context = extract_coupon_context(md_content, result.html)
            if isinstance(parsed_data, dict):
                price_info = parsed_data.get('price') or {}
                if not coupon_context.get('original_price'):
                    coupon_context['original_price'] = price_info.get('original', '')
                if not coupon_context.get('sale_price'):
                    coupon_context['sale_price'] = price_info.get('discounted', '')


            resp_data = {
                "title": title,
                "description": description,
                "image": image or (coupon_data.get("image") if coupon_data else ""),
                "markdown": md_content,
                "screenshots": filtered_screenshots or screenshots[:8] or (coupon_data.get("screenshots") if coupon_data else []),
                "videos": filtered_videos[:10],
                "sourceType": source_type,
                "confidence": confidence,
                "reviews": reviews_list,
                "rating": rating,
                "reviews_count": (parsed_data or {}).get('ratings', {}).get('reviews_count', 'N/A') if isinstance(parsed_data, dict) else 'N/A',
                "parent_asin": (parsed_data or {}).get('parent_asin', '') if isinstance(parsed_data, dict) else '',
                "review_videos": review_videos,
                "buyer_images": buyer_images,
                "review_images": review_images,
                "customer_say": customer_say,
                "review_cards": review_cards,
                "couponCode": coupon_context.get("coupon_code", ""),
                "discountText": coupon_context.get("discount_text", ""),
                "originalPrice": coupon_context.get("original_price", ""),
                "salePrice": coupon_context.get("sale_price", ""),
                "promoHeadline": coupon_context.get("promo_headline", ""),
                "promoBullets": coupon_context.get("promo_bullets", []),
                "ctaText": coupon_context.get("cta_text", ""),
                # Direct Amazon links never go through the koupon.ai/dealseek/affitfy
                # branches (coupon_data stays None there), so isCoupon was always
                # False for them regardless of a real on-page coupon/deal badge.
                # discount_text is the reliable signal here — coupon_code's regex
                # false-positives on ordinary sentences (see coupon_context.py).
                "isCoupon": bool(coupon_context.get("discount_text")),
            }
            if coupon_data:
                resp_data.update({
                    "isCoupon": True,
                    "couponCode": coupon_data.get("couponCode") or resp_data.get("couponCode"),
                    "discount": coupon_data.get("discount") or resp_data.get("discountText"),
                    "discountText": coupon_data.get("discount") or resp_data.get("discountText"),
                    "originalPrice": coupon_data.get("originalPrice") or resp_data.get("originalPrice"),
                    "salePrice": coupon_data.get("salePrice") or resp_data.get("salePrice"),
                    "targetUrl": coupon_data.get("targetUrl") or url,
                })
                code = coupon_data.get("couponCode")
                if code:
                    resp_data["ctaText"] = f"Use code {code}"
                    if not any(code in bullet for bullet in resp_data.get("promoBullets", [])):
                        resp_data["promoBullets"] = [f"Code: {code}"] + resp_data["promoBullets"]
            return resp_data

    except Exception as e:
        if coupon_data:
            print(f"[Crawl Warning] Amazon crawl failed ({e}), falling back to coupon data.")
            return {
                "title": coupon_data.get("title") or "Unknown Product",
                "description": coupon_data.get("description") or "",
                "image": coupon_data.get("image") or "",
                "markdown": f"# Coupon Product: {coupon_data.get('title')}\nPromo Code: {coupon_data.get('couponCode')}\nDiscount: {coupon_data.get('discount')}\n",
                "screenshots": coupon_data.get("screenshots") or [],
                "videos": [],
                "sourceType": "amazon",
                "confidence": 0.8,
                "reviews": [],
                "rating": "N/A",
                "reviews_count": "N/A",
                "buyer_images": [],
                "review_images": [],
                "customer_say": "",
                "review_cards": [],
                "isCoupon": True,
                "couponCode": coupon_data.get("couponCode"),
                "discount": coupon_data.get("discount"),
                "originalPrice": coupon_data.get("originalPrice"),
                "salePrice": coupon_data.get("salePrice"),
                "targetUrl": coupon_data.get("targetUrl") or url,
            }
        if isinstance(e, HTTPException):
            raise e
        error_msg = str(e) or type(e).__name__
        print(f"[Error during crawl] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)



def crawl_product_url(url: str) -> dict[str, object]:
    with _scrape_semaphore:
        result = asyncio.run(_scrape_url(CrawlRequest(url=url)))
    if not isinstance(result, dict):
        raise AppError(
            "PRODUCT_CRAWL_FAILED",
            "The crawler returned an invalid response.",
            status_code=502,
        )
    return result
