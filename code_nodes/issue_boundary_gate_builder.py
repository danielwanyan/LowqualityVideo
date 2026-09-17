import json


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _json_dict(value):
    text = _to_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _signals(video_text_panel):
    parsed = _json_dict(video_text_panel)
    signals = parsed.get("signals")
    return signals if isinstance(signals, dict) else {}


def _data_quality(value):
    return _json_dict(value)


async def main(args: Args) -> Output:
    params = args.params

    video_text_panel = _to_text(params.get("video_text_panel"))
    video_quality = _data_quality(params.get("video_data_quality_json") or params.get("video_data_quality"))
    product_aux_panel = _to_text(params.get("product_aux_panel"))
    product_quality = _data_quality(params.get("product_aux_data_quality_json"))
    signals = _signals(video_text_panel)

    gates = {
        "mfe": {
            "required_claim_source": "frame_list_or_ASR_or_OCR",
            "blocked_claim_sources": [
                "product_image_only",
                "product_detail_page_only",
                "product_review_or_comment",
                "generic_category_expectation",
            ],
            "allowed_claim_strength": [
                "concrete_measurable_claim",
                "medical_or_health_effect_claim",
                "time_bound_or_duration_claim",
                "quantity_or_capacity_claim",
                "physically_impossible_effect",
            ],
            "blocked_claim_strength": [
                "generic_ad_praise",
                "metaphor",
                "ordinary_before_after",
                "normal_cleaning_or_shaving_result",
                "fashion_fit_or_comfort_praise",
            ],
            "sample_signal_hint": bool(signals.get("has_misleading_terms")),
            "instruction": "MFE must be supported by video frame, ASR, or OCR evidence. Do not infer it from product images or product-page copy alone.",
        },
        "ipp": {
            "allowed_difference_types": [
                "core_product_type",
                "core_function",
                "package_count_or_quantity",
                "visible_size_or_dimension",
            ],
            "blocked_difference_types": [
                "color_only",
                "brand_text_only",
                "packaging_language_only",
                "functional_words_only",
                "accessory_or_variant_only",
                "opening_scene_or_prop_only",
            ],
            "product_images_available": bool(product_quality.get("product_images_available")),
            "instruction": "IPP requires a core product contradiction. Do not hit for color, brand text, package language, or functional words alone.",
        },
        "piracy": {
            "minimum_strong_signal_count": 2,
            "strong_signals": [
                "chinese_domestic_ui_or_app_screen",
                "chinese_studio_or_factory_environment_for_non_cn_market",
                "watermark_hiding_or_sandwich_layout",
                "obvious_unrelated_creator_or_source_reuse",
                "blurry_reposted_footage_plus_context_mismatch",
            ],
            "blocked_weak_signals": [
                "replying_to_user_comment",
                "self_verification_or_debunking",
                "same_creator_different_scene",
                "generic_blurry_video",
                "simple_style_shift",
                "ordinary_b_roll",
            ],
            "sample_signal_hint": bool(signals.get("has_pirated_terms")),
            "instruction": "Suspected piracy needs at least two strong internal signals, unless one signal is a clear watermark/copyright reuse pattern.",
        },
        "still_frame": {
            "strictness": "very_high",
            "required_evidence": [
                "sampled_frames_nearly_identical",
                "no_meaningful_camera_movement",
                "no_product_or_pose_state_change",
                "no_substantive_product_demonstration",
            ],
            "blocked_evidence": [
                "angle_shift",
                "lighting_shift",
                "pose_shift",
                "camera_movement",
                "product_movement",
                "different_product_state",
            ],
            "instruction": "Still-frame should almost never hit unless sampled frames are effectively identical and uninformative.",
        },
        "continuity": {
            "priority": "low",
            "strong_hit_examples": [
                "item_taken_from_sealed_package_without_opening",
                "connector_plug_hook_screw_support_bar_or_mounting_structure_impossible",
                "impossible_hand_or_object_contact",
                "object_materialization_that_affects_product_understanding",
            ],
            "blocked_evidence": [
                "missing_intermediate_action_due_to_8_frame_sampling",
                "minor_hand_artifact",
                "lighting_or_angle_change",
                "motion_blur",
                "normal_editing_jump",
            ],
            "instruction": "Continuity is low priority. If evidence can be explained by sparse sampling or normal editing, choose clean.",
        },
    }

    panel_lines = [
        "ISSUE BOUNDARY GATES",
        f"VIDEO_FRAMES_AVAILABLE: {bool(video_quality.get('video_frames_available'))}",
        f"ASR_AVAILABLE: {bool(video_quality.get('asr_available'))}",
        f"OCR_AVAILABLE: {bool(video_quality.get('ocr_available'))}",
        f"PRODUCT_IMAGES_AVAILABLE: {bool(product_quality.get('product_images_available'))}",
        "MFE_CLAIM_GATE: frame_list/ASR/OCR evidence required; product image/detail page alone is blocked.",
        "IPP_DIFFERENCE_GATE: only core product type/function/quantity/size contradictions are allowed.",
        "PIRACY_SIGNAL_GATE: at least two strong internal piracy/reuse signals are required unless watermark/copyright reuse is clear.",
        "STILL_FRAME_GATE: very high strictness; angle/light/pose/camera/product movement blocks still_frame.",
        "CONTINUITY_GATE: low priority; sparse-frame uncertainty defaults to clean.",
        "PRODUCT_AUX_CONTEXT:",
        product_aux_panel,
    ]

    return {
        "issue_boundary_gates_json": json.dumps(gates, ensure_ascii=False),
        "issue_boundary_gate_panel": "\n".join(panel_lines),
    }
