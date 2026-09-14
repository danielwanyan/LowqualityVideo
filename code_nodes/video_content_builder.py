import json
import re
from urllib.parse import urlsplit, urlunsplit


IMAGE_URL_RE = re.compile(r"https?://[^\s\"'<>\\)\]}]+")
IMAGE_MARKER_RE = re.compile(r"\[Image\s*#\s*\d+\]", re.IGNORECASE)
IMAGE_EXT_IN_PATH_RE = re.compile(r"(?i)\.(?:jpe?g|png|webp)(?=/)")
TRAE_FRAME_DIR_RE = re.compile(
    r"(/trae_video_frame_test_\d{8}/)(?!_)(OGV[^/]+)(?<!_)(/frame_\d+\.jpe?g)$",
    re.IGNORECASE,
)
FRAME_SAMPLING_METHOD = "uniform_8_by_video_duration"
FRAME_SAMPLING_NOTE = (
    "frame_list contains up to 8 video frames uniformly sampled across the full video duration "
    "in chronological order; adjacent VIDEO_FRAME entries are neighboring sampled frames, "
    "not frames one second apart."
)


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_is_aigc(value):
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y", "是", "yes/aigc", "aigc"}:
        return "true"
    if text in {"false", "0", "no", "n", "否", "non-aigc", "non_aigc", "not aigc"}:
        return "false"
    return "unknown"


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
        parts = urlsplit(url)

    repaired_path = TRAE_FRAME_DIR_RE.sub(r"\1_\2_\3", parts.path)
    if repaired_path != parts.path:
        parts = parts._replace(path=repaired_path)
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


def _has_any(text, keywords):
    lowered = _to_text(text).lower()
    return any(keyword in lowered for keyword in keywords)


def _contains_cjk(text):
    return bool(re.search(r"[\u4e00-\u9fff]", _to_text(text)))


def _build_text_signals(asr, ocr):
    combined = f"{_to_text(asr)}\n{_to_text(ocr)}"
    lowered = combined.lower()

    hard_sell_terms = [
        "buy now", "add to cart", "cart", "checkout", "discount", "sale",
        "limited", "only today", "today only", "free gift", "buy one get one",
        "last chance", "price drop", "order now", "shop now",
        "kaufen", "bestellen", "angebot", "rabatt", "gratis",
        "comprar", "pedido", "oferta", "descuento",
        "acheter", "commande", "promo", "livraison gratuite",
        "下单", "购买", "折扣", "优惠", "买一送一", "限时", "库存",
    ]
    substantive_terms = [
        "material", "cotton", "polyester", "stainless", "waterproof",
        "size", "capacity", "battery", "ingredient", "how to use",
        "suitable", "compatible", "feature", "function", "made of",
        "usage", "install", "installation", "specification", "dimension",
        "stoff", "baumwolle", "größe", "material", "wasserdicht",
        "tamaño", "capacidad", "ingrediente", "uso",
        "taille", "matiere", "capacité", "ingredient",
        "材质", "尺寸", "容量", "成分", "使用", "安装", "功能", "规格",
    ]
    external_transaction_terms = [
        "paypal", "venmo", "cash app", "cashapp", "zelle", "whatsapp",
        "telegram", "phone number", "call me", "text me", "dm me to buy",
        "link in bio", "website", "offline store", "bank transfer",
        "outside tiktok", "outside the app", "站外", "微信", "支付宝", "私信购买",
    ]
    misleading_terms = [
        "instant", "immediately", "miracle", "guaranteed", "permanent",
        "overnight", "lose weight", "weight loss", "whitening", "cure",
        "diabetes", "grow taller", "doctor recommended", "expert certified",
        "sofort", "wunder", "garantiert", "milagro", "instantáneo",
        "miracle", "garanti", "instantané", "立刻", "马上", "奇迹", "保证",
        "治愈", "减肥", "长高", "医生推荐",
    ]
    pirated_terms = [
        "stolen", "repost", "reposted", "copied", "copy", "credit",
        "original creator", "watermark", "from douyin", "douyin",
        "搬运", "盗用", "盗播", "转载", "原作者", "抖音", "水印",
    ]
    discomfort_terms = [
        "ear cleaning", "ear wax", "insect", "cockroach", "sewer", "drain",
        "dirty", "bloody", "scream", "terrifying", "horror", "恶心",
        "恐怖", "下水道", "昆虫", "尖叫", "耳垢", "掏耳",
    ]
    sexual_terms = [
        "sexy", "sexual", "cleavage", "bikini", "underwear", "lingerie",
        "spend the night", "sleep with", "胸", "内衣", "低俗", "擦边",
        "性暗示", "过夜",
    ]
    dangerous_terms = [
        "fire", "smoke", "explosion", "knife", "weapon", "dangerous",
        "do not try", "unsafe", "火", "烟", "爆炸", "危险", "刀",
    ]

    return {
        "has_hard_sell_terms": _has_any(lowered, hard_sell_terms),
        "has_substantive_product_terms": _has_any(lowered, substantive_terms),
        "has_external_transaction_terms": _has_any(lowered, external_transaction_terms),
        "has_misleading_terms": _has_any(lowered, misleading_terms),
        "has_pirated_terms": _has_any(lowered, pirated_terms),
        "has_discomfort_terms": _has_any(lowered, discomfort_terms),
        "has_sexual_terms": _has_any(lowered, sexual_terms),
        "has_dangerous_terms": _has_any(lowered, dangerous_terms),
        "has_cjk_text": _contains_cjk(combined),
    }


def _preview(text, limit=1200):
    text = _to_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


async def main(args: Args) -> Output:
    params = args.params

    video_id = _to_text(params.get("video_id"))
    url = _to_text(params.get("url"))
    asr = _to_text(params.get("ASR"))
    ocr = _to_text(params.get("OCR"))
    frame_list = _to_text(params.get("frame_list"))
    is_aigc = _normalize_is_aigc(params.get("is_AIGC"))

    frame_urls = _extract_image_urls(frame_list)
    signals = _build_text_signals(asr, ocr)

    manifest_lines = [
        f"VIDEO_ID: {video_id}",
        f"VIDEO_URL_PRESENT: {'yes' if url else 'no'}",
        f"VIDEO_FRAME_COUNT: {len(frame_urls)}",
        f"SAMPLING_METHOD: {FRAME_SAMPLING_METHOD}",
        f"SAMPLING_NOTE: {FRAME_SAMPLING_NOTE}",
    ]
    for idx, frame_url in enumerate(frame_urls):
        manifest_lines.append(
            f"VIDEO_FRAME {idx + 1:03d} | source=frame_list line {idx + 1} | {frame_url}"
        )

    warnings = []
    if frame_urls and len(frame_urls) != 8:
        warnings.append(
            "frame_list does not contain 8 frames; treat provided frames as chronological sampled evidence and do not infer exact elapsed time"
        )
    if not frame_urls:
        warnings.append("frame_list is empty; do not make visual claims about video frames")
    if not asr and not ocr:
        warnings.append("ASR and OCR are both empty")
    if is_aigc == "unknown":
        warnings.append("is_AIGC is empty or not recognized; treat as unknown attribute")

    data_quality = {
        "video_frames_available": len(frame_urls) > 0,
        "video_frame_count": len(frame_urls),
        "expected_video_frame_count": 8,
        "frame_sampling_method": FRAME_SAMPLING_METHOD,
        "frame_sampling_note": FRAME_SAMPLING_NOTE,
        "frame_interval_seconds_known": False,
        "asr_available": bool(asr),
        "ocr_available": bool(ocr),
        "video_url_available": bool(url),
        "is_AIGC": is_aigc,
        "warnings": warnings,
    }

    video_text_panel = {
        "asr_text": _preview(asr),
        "ocr_text": _preview(ocr),
        "notes": [
            "ASR and OCR are video content evidence, not product metadata.",
            FRAME_SAMPLING_NOTE,
            "Text signals are attention hints only; final issue hits require concrete evidence.",
        ],
    }

    aigc_attribute_panel = {
        "is_AIGC": is_aigc,
        "usage": [
            "is_AIGC is an attribute, not a violation.",
            "is_AIGC only increases attention for unrealistic_or_continuity_error.",
            "is_AIGC must not increase attention for misleading_functionality_and_effect, no_physical_product_display, still_frame, or pirated labels.",
            "A hit still requires concrete frame, ASR, OCR, or product image evidence.",
        ],
    }

    video_signal_panel = {
        "signals": signals,
        "candidate_attention": {
            "only_marketing_sales_pitches": signals["has_hard_sell_terms"]
            and not signals["has_substantive_product_terms"],
            "out_of_app_transactions": signals["has_external_transaction_terms"],
            "misleading_functionality_and_effect": signals["has_misleading_terms"],
            "potential_pirated_or_pirated": signals["has_pirated_terms"],
            "non_native": signals["has_cjk_text"],
            "disgusting_and_terrifying": signals["has_discomfort_terms"],
            "pornography_perception": signals["has_sexual_terms"],
            "dangerous_behavior": signals["has_dangerous_terms"],
            "unrealistic_or_continuity_error": is_aigc == "true"
            or signals["has_misleading_terms"]
            or signals["has_pirated_terms"],
        },
        "notes": [
            "candidate_attention is not a final decision.",
            "Use video frames, ASR/OCR, and product reference evidence as the analysis scope.",
        ],
    }

    ret = {
        "video_frame_urls": frame_urls,
        "video_frame_manifest": "\n".join(manifest_lines),
        "video_text_panel": json.dumps(video_text_panel, ensure_ascii=False),
        "aigc_attribute_panel": json.dumps(aigc_attribute_panel, ensure_ascii=False),
        "video_signal_panel": json.dumps(video_signal_panel, ensure_ascii=False),
        "video_data_quality": json.dumps(data_quality, ensure_ascii=False),
    }
    return ret
