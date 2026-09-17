import json


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
        return [line.strip() for line in text.splitlines() if line.strip()]
    return []


def _json_dict(value):
    text = _to_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _bool(data, key):
    return bool(data.get(key))


def _build_all_image_manifest(product_urls, frame_urls):
    lines = []
    image_index = 0
    for product_idx, url in enumerate(product_urls):
        lines.append(
            f"IMAGE_INDEX {image_index:03d} | PRODUCT_IMAGE {product_idx + 1:03d} | product_local_index={product_idx} | {url}"
        )
        image_index += 1
    for frame_idx, url in enumerate(frame_urls):
        lines.append(
            f"IMAGE_INDEX {image_index:03d} | VIDEO_FRAME {frame_idx + 1:03d} | frame_list_line={frame_idx + 1} | {url}"
        )
        image_index += 1
    return "\n".join(lines) if lines else "NO_IMAGES_AVAILABLE"


async def main(args: Args) -> Output:
    params = args.params

    product_image_urls = _to_list(params.get("product_image_urls"))
    video_frame_urls = _to_list(params.get("video_frame_urls"))
    video_frame_manifest = _to_text(params.get("video_frame_manifest"))
    product_image_manifest = _to_text(params.get("product_image_manifest"))
    video_data_quality = _json_dict(params.get("video_data_quality_json") or params.get("video_data_quality"))
    product_quality = _json_dict(params.get("product_aux_data_quality_json"))
    boundary_attention_packet = _to_text(params.get("boundary_attention_packet"))
    allowed_issue_types = _to_text(params.get("allowed_issue_types"))

    video_frames_available = bool(video_frame_urls) and _bool(video_data_quality, "video_frames_available")
    product_images_available = bool(product_image_urls) and _bool(product_quality, "product_images_available")
    asr_available = _bool(video_data_quality, "asr_available")
    ocr_available = _bool(video_data_quality, "ocr_available")
    text_available = asr_available or ocr_available
    country_available = _bool(product_quality, "country_available")

    forbidden_claims = [
        "不要输出人工复核类第三结果；只能输出 problematic 或 clean。",
        "不要输出商品侧标签。",
        "不要使用展示或追溯字段作为判断证据。",
    ]
    if not video_frames_available:
        forbidden_claims.append("不要描述视频画面证据；frame_list 缺失或不可用。")
        forbidden_claims.append("如果没有其他强文本证据，choose clean，并在 tagsAttribute 中加入 视频不可见。")
    if not product_images_available:
        forbidden_claims.append("不要进行商品图视觉对比；images 缺失或不可用。")
    if not text_available:
        forbidden_claims.append("不要判断 ASR/OCR 文本类问题，例如仅营销叫卖或站外引流。")
    if not country_available:
        forbidden_claims.append("不要推断国家或市场语境。")

    all_image_urls = product_image_urls + video_frame_urls
    all_image_manifest = _build_all_image_manifest(product_image_urls, video_frame_urls)
    final_context = "\n\n".join([
        "VIDEO-FIRST LOWQUALITY REVIEW CONTEXT",
        "Allowed final decisions: problematic, clean.",
        "Default rule: if evidence is weak, ambiguous, incomplete, or only suspicious, choose clean and explain the boundary.",
        "VISUAL INPUT MANIFEST",
        all_image_manifest,
        "VIDEO FRAME MANIFEST",
        video_frame_manifest,
        "PRODUCT IMAGE MANIFEST",
        product_image_manifest,
        "BOUNDARY ATTENTION",
        boundary_attention_packet,
        "FORBIDDEN CLAIMS",
        "\n".join(f"- {claim}" for claim in forbidden_claims),
    ]).strip()

    gate_panel = "\n".join([
        "证据可用性检查",
        f"视频帧可用: {video_frames_available}",
        f"商品图片可用: {product_images_available}",
        f"ASR 可用: {asr_available}",
        f"OCR 可用: {ocr_available}",
        f"国家字段可用: {country_available}",
        "允许输出: problematic, clean",
        "不允许输出第三种裁决",
        "视频不可见" if not video_frames_available else "视频帧可用于视觉判断",
        "禁止事项:",
        "\n".join(f"- {claim}" for claim in forbidden_claims) if forbidden_claims else "- none",
    ])

    return {
        "gated_all_image_urls": all_image_urls,
        "gated_all_image_manifest": all_image_manifest,
        "evidence_gate_panel": gate_panel,
        "forbidden_claims": "\n".join(forbidden_claims),
        "allowed_issue_types": allowed_issue_types,
        "final_reviewer_context": final_context,
    }
