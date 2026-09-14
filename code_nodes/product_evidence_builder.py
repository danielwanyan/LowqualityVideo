import json
import re
from urllib.parse import urlsplit, urlunsplit


IMAGE_URL_RE = re.compile(r"https?://[^\s\"'<>\\)\]}]+")
IMAGE_MARKER_RE = re.compile(r"\[Image\s*#\s*\d+\]", re.IGNORECASE)
IMAGE_EXT_IN_PATH_RE = re.compile(r"(?i)\.(?:jpe?g|png|webp)(?=/)")


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _clean_image_url(value):
    url = IMAGE_MARKER_RE.sub(" ", _to_text(value)).strip()
    url = url.strip("\"'[],; ")
    if not url:
        return ""

    starts = [match.start() for match in re.finditer(r"https?://", url)]
    if not starts:
        return ""
    if len(starts) > 1:
        url = url[starts[-1]:]

    url = url.rstrip("\"'[],; )]}")
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return ""

    match = IMAGE_EXT_IN_PATH_RE.search(parts.path)
    if match:
        parts = parts._replace(path=parts.path[:match.end()], query="", fragment="")
        url = urlunsplit(parts)
    return url


def _extract_image_urls(value):
    raw = _to_text(value)
    if not raw:
        return []

    candidates = []

    def collect(obj):
        if obj is None:
            return
        if isinstance(obj, str):
            text = IMAGE_MARKER_RE.sub(" ", obj)
            candidates.extend(IMAGE_URL_RE.findall(text))
            if text.strip().startswith(("http://", "https://")):
                candidates.append(text.strip())
        elif isinstance(obj, dict):
            for item in obj.values():
                collect(item)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    try:
        collect(json.loads(raw))
    except Exception:
        pass
    collect(raw)

    urls = []
    seen = set()
    for candidate in candidates:
        cleaned = _clean_image_url(candidate)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


async def main(args: Args) -> Output:
    params = args.params

    product_id = _to_text(params.get("product_id"))
    images = _to_text(params.get("images"))
    seller_id_str = _to_text(params.get("seller_id_str"))
    country = _to_text(params.get("country"))

    image_urls = _extract_image_urls(images)

    manifest_lines = [
        f"PRODUCT_ID: {product_id}",
        f"SELLER_ID_STR: {seller_id_str}",
        f"COUNTRY: {country}",
        f"PRODUCT_IMAGE_COUNT: {len(image_urls)}",
    ]
    for idx, image_url in enumerate(image_urls):
        manifest_lines.append(
            f"PRODUCT_IMAGE {idx + 1:03d} | product_local_index={idx} | {image_url}"
        )

    identity_panel = {
        "product_id": product_id,
        "seller_id_str": seller_id_str,
        "country": country,
        "product_image_count": len(image_urls),
        "notes": [
            "Product images are product reference evidence.",
            "Use product-local image indices when citing product images.",
            "Do not use product metadata alone to prove visual consistency.",
            "Strong inconsistent_product_promotion requires product image evidence.",
        ],
    }

    warnings = []
    if not image_urls:
        warnings.append("images is empty or invalid; do not make product-image visual claims")
    if not product_id:
        warnings.append("product_id is empty")
    if not seller_id_str:
        warnings.append("seller_id_str is empty")
    if not country:
        warnings.append("country is empty")

    data_quality = {
        "product_id_available": bool(product_id),
        "seller_id_available": bool(seller_id_str),
        "country_available": bool(country),
        "product_images_available": len(image_urls) > 0,
        "product_image_count": len(image_urls),
        "warnings": warnings,
    }

    ret = {
        "product_image_urls": image_urls,
        "product_image_manifest": "\n".join(manifest_lines),
        "product_identity_panel": json.dumps(identity_panel, ensure_ascii=False),
        "product_data_quality": json.dumps(data_quality, ensure_ascii=False),
    }
    return ret
