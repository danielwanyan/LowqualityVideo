import json
import re


ALLOWED_ISSUES = [
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
ALLOWED_ISSUES_SET = set(ALLOWED_ISSUES)
ALLOWED_PRIMARY = ALLOWED_ISSUES_SET | {"none"}
ALLOWED_OVERALL = {"problematic", "manual_review", "clean"}
ALLOWED_AIGC = {"true", "false", "unknown"}
ALLOWED_DECISIONS = {"hit", "no_hit", "uncertain"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


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


def _strip_code_fence(text):
    raw = _to_text(text)
    if not raw.startswith("```"):
        return raw
    match = re.match(r"^```(?:json|JSON)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip("`").strip()


def _extract_llm_output(params):
    for key in (
        "llm_raw_output",
        "model_output",
        "reviewer_output",
        "SOP_Multimodal_Risk_Reviewer",
        "output",
    ):
        value = params.get(key)
        if value not in (None, ""):
            return value
    return ""


def _parse_payload(raw):
    if isinstance(raw, dict):
        return raw, None
    text = _strip_code_fence(raw)
    if not text:
        return None, "JSON parse failed: empty LLM output"
    try:
        parsed = json.loads(text)
    except Exception as exc:
        return None, f"JSON parse failed: {exc}"
    if not isinstance(parsed, dict):
        return None, "JSON parse failed: top-level output is not an object"
    return parsed, None


def _safe_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return [text]
    return []


def _safe_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _to_bool(value):
    if isinstance(value, bool):
        return value
    text = _to_text(value).lower()
    if text in {"true", "1", "yes", "y", "是"}:
        return True
    if text in {"false", "0", "no", "n", "否", ""}:
        return False
    return bool(value)


def _default_issue_result():
    return {
        "decision": "no_hit",
        "evidence_cn": "",
        "confidence": "low",
    }


def _default_manual_review(video_id, is_aigc, errors):
    payload = {
        "video_id": video_id,
        "overall_decision": "manual_review",
        "primary_issue_type": "none",
        "detected_issue_types": [],
        "is_AIGC": is_aigc,
        "issue_results": {issue: _default_issue_result() for issue in ALLOWED_ISSUES},
        "data_quality": {
            "video_frames_available": False,
            "product_images_available": False,
            "asr_available": False,
            "ocr_available": False,
            "missing_or_weak_inputs": ["llm_output_parse_failed"],
        },
        "manual_review_reasons": ["LLM 输出无法解析或结构不合规，需要人工复核。"],
        "summary_cn": "LLM 输出解析失败或结构不合规。",
        "final_reason_cn": "解析失败，不能静默判定为 clean，已转为 manual_review。",
    }
    return _result(payload, "failed", errors)


def _normalize_issue_result(value):
    result = _default_issue_result()
    changed = False
    if not isinstance(value, dict):
        return result, bool(value)

    decision = _to_text(value.get("decision"))
    confidence = _to_text(value.get("confidence"))
    if decision in ALLOWED_DECISIONS:
        result["decision"] = decision
    elif decision:
        changed = True
    if confidence in ALLOWED_CONFIDENCE:
        result["confidence"] = confidence
    elif confidence:
        changed = True
    result["evidence_cn"] = _to_text(value.get("evidence_cn"))
    if result["evidence_cn"] != _to_text(value.get("evidence_cn")):
        changed = True
    return result, changed


def _result(payload, status, errors):
    return {
        "validated_json": json.dumps(payload, ensure_ascii=False),
        "validation_status": status,
        "validation_errors": "\n".join(errors),
        "video_id": _to_text(payload.get("video_id")),
        "overall_decision": _to_text(payload.get("overall_decision")),
        "primary_issue_type": _to_text(payload.get("primary_issue_type")),
        "detected_issue_types": payload.get("detected_issue_types") or [],
        "is_AIGC": _to_text(payload.get("is_AIGC")),
        "issue_results_json": json.dumps(payload.get("issue_results") or {}, ensure_ascii=False),
        "data_quality_json": json.dumps(payload.get("data_quality") or {}, ensure_ascii=False),
        "manual_review_reasons_json": json.dumps(payload.get("manual_review_reasons") or [], ensure_ascii=False),
        "summary_cn": _to_text(payload.get("summary_cn")),
        "final_reason_cn": _to_text(payload.get("final_reason_cn")),
    }


async def main(args: Args) -> Output:
    params = args.params
    fallback_video_id = _to_text(params.get("video_id"))
    fallback_is_aigc = _normalize_is_aigc(params.get("is_AIGC"))
    raw_output = _extract_llm_output(params)

    payload, parse_error = _parse_payload(raw_output)
    if parse_error:
        return _default_manual_review(fallback_video_id, fallback_is_aigc, [parse_error])

    errors = []
    fixed = False

    video_id = _to_text(payload.get("video_id")) or fallback_video_id
    if video_id != payload.get("video_id"):
        fixed = True
        errors.append("missing video_id filled from Start input")

    overall_decision = _to_text(payload.get("overall_decision"))
    if overall_decision not in ALLOWED_OVERALL:
        overall_decision = "manual_review"
        fixed = True
        errors.append("illegal overall_decision changed to manual_review")

    detected_issue_types = []
    removed_issue_types = []
    for issue in _safe_list(payload.get("detected_issue_types")):
        issue_text = _to_text(issue)
        if issue_text in ALLOWED_ISSUES_SET and issue_text not in detected_issue_types:
            detected_issue_types.append(issue_text)
        elif issue_text:
            removed_issue_types.append(issue_text)
    if removed_issue_types:
        overall_decision = "manual_review"
        fixed = True
        errors.append(f"illegal detected_issue_types removed: {', '.join(removed_issue_types)}")

    primary_issue_type = _to_text(payload.get("primary_issue_type"))
    if primary_issue_type not in ALLOWED_PRIMARY:
        primary_issue_type = "none"
        overall_decision = "manual_review"
        fixed = True
        errors.append("illegal primary_issue_type changed to none")

    if overall_decision == "problematic" and primary_issue_type not in detected_issue_types:
        if detected_issue_types:
            primary_issue_type = detected_issue_types[0]
            fixed = True
            errors.append("primary_issue_type changed to first detected issue")
        else:
            overall_decision = "manual_review"
            primary_issue_type = "none"
            fixed = True
            errors.append("problematic output without detected_issue_types changed to manual_review")

    if overall_decision == "clean" and detected_issue_types:
        overall_decision = "manual_review"
        fixed = True
        errors.append("clean output cannot contain detected_issue_types")

    if overall_decision == "clean" and primary_issue_type != "none":
        primary_issue_type = "none"
        overall_decision = "manual_review"
        fixed = True
        errors.append("clean output cannot contain non-none primary_issue_type")

    is_aigc = _to_text(payload.get("is_AIGC")).lower()
    if is_aigc not in ALLOWED_AIGC:
        is_aigc = fallback_is_aigc
        fixed = True
        errors.append("illegal or missing is_AIGC normalized from Start input")

    issue_results = _safe_dict(payload.get("issue_results"))
    normalized_issue_results = {}
    invalid_issue_result_enums = False
    for issue in ALLOWED_ISSUES:
        normalized_issue_results[issue], changed = _normalize_issue_result(issue_results.get(issue))
        invalid_issue_result_enums = invalid_issue_result_enums or changed
    if set(issue_results.keys()) != set(ALLOWED_ISSUES):
        fixed = True
        errors.append("issue_results normalized to exactly 15 issue keys")
    if invalid_issue_result_enums:
        fixed = True
        errors.append("invalid issue_results enum values normalized")

    missing_hit_issues = []
    for issue, issue_result in normalized_issue_results.items():
        if issue_result["decision"] == "hit" and issue not in detected_issue_types:
            detected_issue_types.append(issue)
            missing_hit_issues.append(issue)
    if missing_hit_issues:
        fixed = True
        errors.append(f"hit issue_results added to detected_issue_types: {', '.join(missing_hit_issues)}")

    uncertain_issues = [
        issue
        for issue, issue_result in normalized_issue_results.items()
        if issue_result["decision"] == "uncertain"
    ]
    if overall_decision == "clean" and missing_hit_issues:
        overall_decision = "manual_review"
        fixed = True
        errors.append("clean output cannot contain hit issue_results")
    if overall_decision == "clean" and uncertain_issues:
        overall_decision = "manual_review"
        fixed = True
        errors.append(f"clean output cannot contain uncertain issue_results: {', '.join(uncertain_issues)}")

    raw_data_quality = _safe_dict(payload.get("data_quality"))
    unsupported_data_quality_fields = sorted(
        key
        for key in raw_data_quality
        if key
        not in {
            "video_frames_available",
            "product_images_available",
            "asr_available",
            "ocr_available",
            "missing_or_weak_inputs",
        }
    )
    if unsupported_data_quality_fields:
        fixed = True
        errors.append(
            f"unsupported data_quality fields removed: {', '.join(unsupported_data_quality_fields)}"
        )
    data_quality = {}
    for key in (
        "video_frames_available",
        "product_images_available",
        "asr_available",
        "ocr_available",
    ):
        data_quality[key] = _to_bool(raw_data_quality.get(key))
    missing_or_weak_inputs = _safe_list(raw_data_quality.get("missing_or_weak_inputs"))
    data_quality["missing_or_weak_inputs"] = [_to_text(item) for item in missing_or_weak_inputs if _to_text(item)]

    manual_review_reasons = [
        _to_text(item)
        for item in _safe_list(payload.get("manual_review_reasons"))
        if _to_text(item)
    ]
    if overall_decision == "manual_review" and errors:
        manual_review_reasons.extend([f"schema_validation: {error}" for error in errors])

    normalized = {
        "video_id": video_id,
        "overall_decision": overall_decision,
        "primary_issue_type": primary_issue_type,
        "detected_issue_types": detected_issue_types,
        "is_AIGC": is_aigc,
        "issue_results": normalized_issue_results,
        "data_quality": data_quality,
        "manual_review_reasons": manual_review_reasons,
        "summary_cn": _to_text(payload.get("summary_cn")),
        "final_reason_cn": _to_text(payload.get("final_reason_cn")),
    }

    status = "fixed" if fixed else "ok"
    return _result(normalized, status, errors)
