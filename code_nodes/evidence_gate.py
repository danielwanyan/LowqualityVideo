import json


VISUAL_ISSUE_TYPES = {
    "potential_pirated",
    "pirated_content",
    "still_frame",
    "disgusting_and_terrifying",
    "pornography_perception",
    "unrealistic_or_continuity_error",
    "irrelevant_promotion",
    "dangerous_behavior",
}

PRODUCT_IMAGE_REQUIRED_TYPES = {
    "inconsistent_product_promotion",
}

TEXT_REQUIRED_TYPES = {
    "only_marketing_sales_pitches",
    "non_native",
}

ALL_ISSUE_TYPES = [
    "potential_pirated",
    "irrelevant_promotion",
    "pirated_content",
    "inconsistent_product_promotion",
    "non_native",
    "still_frame",
    "out_of_app_transactions",
    "misleading_functionality_and_effect",
    "dangerous_behavior",
    "disgusting_and_terrifying",
    "description_not_detailed",
    "only_marketing_sales_pitches",
    "pornography_perception",
    "no_physical_product_display",
    "unrealistic_or_continuity_error",
]


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


def _parse_json(value, fallback):
    text = _to_text(value)
    if not text:
        return fallback
    try:
        parsed = json.loads(text)
        return parsed
    except Exception:
        return fallback


def _bool_from_json(value, key):
    parsed = _parse_json(value, {})
    if isinstance(parsed, dict):
        return bool(parsed.get(key))
    return False


def _int_from_json(value, key):
    parsed = _parse_json(value, {})
    if isinstance(parsed, dict):
        try:
            return int(parsed.get(key) or 0)
        except Exception:
            return 0
    return 0


def _cluster_types(comment_issue_clusters):
    parsed = _parse_json(comment_issue_clusters, {})
    if isinstance(parsed, dict) and isinstance(parsed.get("cluster_types"), list):
        return {str(item).strip() for item in parsed["cluster_types"] if str(item).strip()}
    return set()


async def main(args: Args) -> Output:
    params = args.params

    all_image_urls = _to_list(params.get("all_image_urls"))
    all_image_manifest = _to_text(params.get("all_image_manifest"))
    risk_attention_packet = _to_text(params.get("risk_attention_packet"))
    missing_data_panel = _to_text(params.get("missing_data_panel"))

    product_image_urls = _to_list(params.get("product_image_urls"))
    video_frame_urls = _to_list(params.get("video_frame_urls"))
    video_data_quality = _to_text(params.get("video_data_quality"))
    product_data_quality = _to_text(params.get("product_data_quality"))
    comment_data_quality = _to_text(params.get("comment_data_quality"))
    comment_issue_clusters = _to_text(params.get("comment_issue_clusters"))

    video_frames_available = bool(video_frame_urls) and _bool_from_json(
        video_data_quality, "video_frames_available"
    )
    product_images_available = bool(product_image_urls) and _bool_from_json(
        product_data_quality, "product_images_available"
    )
    asr_available = _bool_from_json(video_data_quality, "asr_available")
    ocr_available = _bool_from_json(video_data_quality, "ocr_available")
    text_available = asr_available or ocr_available
    comments_available = _bool_from_json(comment_data_quality, "comments_available")
    product_review_summary_available = _bool_from_json(
        comment_data_quality, "product_review_summary_available"
    )
    meaningful_comment_count = _int_from_json(comment_data_quality, "meaningful_comment_count")
    comment_or_review_available = (
        comments_available or product_review_summary_available or meaningful_comment_count > 0
    )
    clusters = _cluster_types(comment_issue_clusters)
    comment_only_piracy_signal = (
        "pirated_or_reposted_claim" in clusters
        and not video_frames_available
        and not text_available
    )

    allowed_issue_types = set(ALL_ISSUE_TYPES)
    forbidden_claims = []

    if not video_frames_available:
        allowed_issue_types.difference_update(VISUAL_ISSUE_TYPES)
        forbidden_claims.append(
            "Do not make video-frame visual claims when frame_list is empty or unusable."
        )
        forbidden_claims.append(
            "Do not hit still_frame, visual pirated/potential pirated, visual pornography, disgusting/terrifying visuals, dangerous visual behavior, or unrealistic/continuity errors without video frames."
        )

    if not product_images_available:
        allowed_issue_types.difference_update(PRODUCT_IMAGE_REQUIRED_TYPES)
        forbidden_claims.append(
            "Do not make strong inconsistent_product_promotion claims when product images are missing or invalid."
        )

    if not text_available:
        allowed_issue_types.difference_update(TEXT_REQUIRED_TYPES)
        forbidden_claims.append(
            "Do not hit text-only only_marketing_sales_pitches or non_native from missing ASR/OCR."
        )

    if comment_only_piracy_signal:
        allowed_issue_types.discard("pirated_content")
        allowed_issue_types.discard("potential_pirated")
        forbidden_claims.append(
            "Comments alone cannot support pirated_content or potential_pirated; require frame or ASR/OCR evidence."
        )

    all_core_evidence_missing = (
        not video_frames_available
        and not product_images_available
        and not text_available
        and not comment_or_review_available
    )
    if all_core_evidence_missing:
        recommended_decision_floor = "manual_review_for_data_insufficiency"
    elif comment_only_piracy_signal:
        recommended_decision_floor = "manual_review_for_comment_only_piracy_signal"
    elif not video_frames_available and (text_available or comment_or_review_available):
        recommended_decision_floor = "manual_review_when_visual_evidence_missing"
    elif not product_images_available and text_available:
        recommended_decision_floor = "manual_review_when_product_reference_missing"
    else:
        recommended_decision_floor = "no_floor"

    evidence_status = {
        "video_frames_available": video_frames_available,
        "product_images_available": product_images_available,
        "asr_available": asr_available,
        "ocr_available": ocr_available,
        "text_available": text_available,
        "comments_available": comments_available,
        "product_review_summary_available": product_review_summary_available,
        "meaningful_comment_count": meaningful_comment_count,
        "comment_or_review_available": comment_or_review_available,
        "comment_only_piracy_signal": comment_only_piracy_signal,
        "all_core_evidence_missing": all_core_evidence_missing,
        "allowed_issue_types": sorted(allowed_issue_types),
        "recommended_decision_floor": recommended_decision_floor,
    }

    gate_panel = "\n".join([
        "EVIDENCE GATE",
        f"video_frames_available: {video_frames_available}",
        f"product_images_available: {product_images_available}",
        f"text_available_ASR_or_OCR: {text_available}",
        f"comments_available: {comments_available}",
        f"product_review_summary_available: {product_review_summary_available}",
        f"comment_only_piracy_signal: {comment_only_piracy_signal}",
        f"allowed_issue_types: {', '.join(sorted(allowed_issue_types)) if allowed_issue_types else 'none'}",
        f"recommended_decision_floor: {recommended_decision_floor}",
        "FORBIDDEN CLAIMS:",
        "\n".join(f"- {claim}" for claim in forbidden_claims) if forbidden_claims else "- none",
        "MISSING DATA PANEL:",
        missing_data_panel,
    ])

    gated_risk_attention_packet = "\n\n".join([
        risk_attention_packet,
        gate_panel,
        "The final reviewer must obey the Evidence Gate above. If a claim is forbidden, do not make that claim even if the general rules mention it.",
    ]).strip()

    ret = {
        "gated_all_image_urls": all_image_urls,
        "gated_all_image_manifest": all_image_manifest,
        "evidence_gate_panel": gate_panel,
        "gated_risk_attention_packet": gated_risk_attention_packet,
        "evidence_status_json": json.dumps(evidence_status, ensure_ascii=False),
        "allowed_issue_types": ", ".join(sorted(allowed_issue_types)),
        "forbidden_claims": "\n".join(forbidden_claims),
        "recommended_decision_floor": recommended_decision_floor,
    }
    return ret
