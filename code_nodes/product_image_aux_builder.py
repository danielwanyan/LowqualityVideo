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


def _parse_image_urls(images):
    raw = _to_text(images)
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
            for value in obj.values():
                collect(value)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    try:
        collect(json.loads(raw))
    except Exception:
        pass
    collect(raw)

    deduped = []
    seen = set()
    for candidate in candidates:
        cleaned = _clean_image_url(candidate)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped


async def main(args: Args) -> Output:
    params = args.params

    images = _to_text(params.get("images"))
    country = _to_text(params.get("country"))
    image_urls = _parse_image_urls(images)

    manifest_lines = [
        f"COUNTRY: {country or 'unknown'}",
        f"PRODUCT_IMAGE_COUNT: {len(image_urls)}",
    ]
    for idx, image_url in enumerate(image_urls):
        manifest_lines.append(
            f"PRODUCT_IMAGE {idx + 1:03d} | product_local_index={idx} | {image_url}"
        )

    data_quality = {
        "country_available": bool(country),
        "product_images_available": len(image_urls) > 0,
        "product_image_count": len(image_urls),
        "warnings": [],
    }
    if not image_urls:
        data_quality["warnings"].append(
            "images is empty or invalid; do not make product-image visual comparison claims"
        )
    if not country:
        data_quality["warnings"].append("country is empty; do not infer market context")

    product_aux_panel = "\n".join([
        "PRODUCT IMAGE AUXILIARY EVIDENCE",
        f"COUNTRY: {country or 'unknown'}",
        f"PRODUCT_IMAGE_COUNT: {len(image_urls)}",
        "ROLE: Product images and country are auxiliary evidence for video low-quality review only.",
        "ALLOWED: compare the shown or described video product against product images.",
        "ALLOWED: use product images to identify visible product promises that the video may contradict.",
        "ALLOWED: use country as language and market context only, not as a standalone hit reason.",
        "FORBIDDEN: do not judge product quality.",
        "FORBIDDEN: do not use display-only row fields as evidence.",
        "FORBIDDEN: do not output product-side labels.",
    ])

    return {
        "product_image_urls": image_urls,
        "product_image_manifest": "\n".join(manifest_lines),
        "product_aux_panel": product_aux_panel,
        "product_aux_data_quality_json": json.dumps(data_quality, ensure_ascii=False),
    }
