import json


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


def _compact(value, limit=1800):
    text = _to_text(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


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
    if not lines:
        return "NO_IMAGES_AVAILABLE"
    return "\n".join(lines)


def _build_missing_data_panel(product_urls, frame_urls, video_data_quality, product_data_quality, comment_data_quality):
    lines = [
        f"PRODUCT_IMAGE_COUNT: {len(product_urls)}",
        f"VIDEO_FRAME_COUNT: {len(frame_urls)}",
        f"VIDEO_DATA_QUALITY: {_compact(video_data_quality, 900)}",
        f"PRODUCT_DATA_QUALITY: {_compact(product_data_quality, 900)}",
        f"COMMENT_DATA_QUALITY: {_compact(comment_data_quality, 900)}",
    ]
    if not product_urls:
        lines.append("WARNING: product images are missing; do not make strong inconsistent_product_promotion claims.")
    if not frame_urls:
        lines.append("WARNING: video frames are missing; do not make video-frame visual claims.")
    return "\n".join(lines)


async def main(args: Args) -> Output:
    params = args.params

    video_frame_urls = _to_list(params.get("video_frame_urls"))
    product_image_urls = _to_list(params.get("product_image_urls"))

    video_frame_manifest = _to_text(params.get("video_frame_manifest"))
    video_text_panel = _to_text(params.get("video_text_panel"))
    aigc_attribute_panel = _to_text(params.get("aigc_attribute_panel"))
    video_signal_panel = _to_text(params.get("video_signal_panel"))
    video_data_quality = _to_text(params.get("video_data_quality"))

    product_image_manifest = _to_text(params.get("product_image_manifest"))
    product_identity_panel = _to_text(params.get("product_identity_panel"))
    product_data_quality = _to_text(params.get("product_data_quality"))

    comment_risk_summary = _to_text(params.get("comment_risk_summary"))
    comment_issue_clusters = _to_text(params.get("comment_issue_clusters"))
    representative_comment_quotes = _to_text(params.get("representative_comment_quotes"))
    comment_data_quality = _to_text(params.get("comment_data_quality"))

    rules_context = _to_text(params.get("rules_context"))
    matched_rule_families = _to_text(params.get("matched_rule_families"))

    all_image_urls = product_image_urls + video_frame_urls
    all_image_manifest = _build_all_image_manifest(product_image_urls, video_frame_urls)
    missing_data_panel = _build_missing_data_panel(
        product_image_urls,
        video_frame_urls,
        video_data_quality,
        product_data_quality,
        comment_data_quality,
    )

    product_comparison_tasks = "\n".join([
        "PRODUCT / VIDEO COMPARISON TASKS",
        f"FRAME SAMPLING CONTRACT: {FRAME_SAMPLING_NOTE}",
        "1. Treat PRODUCT_IMAGE entries as bound product reference images.",
        "2. Treat VIDEO_FRAME entries as video content evidence.",
        "3. Compare physical products shown in VIDEO_FRAME images against all PRODUCT_IMAGE images.",
        "4. Use product-local indices when citing product images; do not confuse them with global IMAGE_INDEX.",
        "5. Strong inconsistent_product_promotion requires product image evidence.",
        "6. Check no_physical_product_display only when the video explains or promotes a product but physical product/package evidence is absent or only static/cutout/screenshot.",
        "7. Check irrelevant_promotion when the main video topic is unrelated to the bound product.",
        "8. Check potential_pirated and pirated_content only with strong internal frame/ASR/OCR evidence; comments alone are insufficient.",
        "9. Do not use external Pearl fields, Similar Video tab, creator profile, or penalty records.",
        "10. Do not claim exact elapsed time between frames unless explicit timestamps are provided.",
    ])

    comment_evidence_panel = "\n".join([
        "COMMENT / REVIEW SUPPORTING SIGNALS",
        f"COMMENT_RISK_SUMMARY:\n{_compact(comment_risk_summary, 1200)}",
        f"COMMENT_ISSUE_CLUSTERS:\n{_compact(comment_issue_clusters, 1600)}",
        f"REPRESENTATIVE_COMMENT_QUOTES:\n{_compact(representative_comment_quotes, 1200)}",
        "Comments are supporting signals only. For pirated labels, comments must be supported by frame or ASR/OCR evidence.",
    ])

    risk_attention_packet = "\n\n".join([
        "PROJECT: LowqualityVideo",
        "SCOPE: Use only the 15 in-scope issue types plus none. Do not cover the complete SOP.",
        f"FRAME SAMPLING CONTRACT: {FRAME_SAMPLING_NOTE}",
        "VISUAL INPUT ORDER",
        all_image_manifest,
        "VIDEO CONTENT EVIDENCE",
        f"VIDEO_FRAME_MANIFEST:\n{_compact(video_frame_manifest, 1500)}",
        f"VIDEO_TEXT_PANEL:\n{_compact(video_text_panel, 1800)}",
        f"AIGC_ATTRIBUTE_PANEL:\n{_compact(aigc_attribute_panel, 900)}",
        f"VIDEO_SIGNAL_PANEL:\n{_compact(video_signal_panel, 1600)}",
        "PRODUCT REFERENCE EVIDENCE",
        f"PRODUCT_IMAGE_MANIFEST:\n{_compact(product_image_manifest, 1500)}",
        f"PRODUCT_IDENTITY_PANEL:\n{_compact(product_identity_panel, 1200)}",
        comment_evidence_panel,
        "RULE ATTENTION",
        f"MATCHED_RULE_FAMILIES: {matched_rule_families or 'none'}",
        f"RULES_CONTEXT:\n{_compact(rules_context, 2600)}",
        "MISSING DATA / DO-NOT-HALLUCINATE PANEL",
        missing_data_panel,
        product_comparison_tasks,
    ])

    ret = {
        "all_image_urls": all_image_urls,
        "all_image_manifest": all_image_manifest,
        "risk_attention_packet": risk_attention_packet,
        "missing_data_panel": missing_data_panel,
    }
    return ret
