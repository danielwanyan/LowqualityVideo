import json


DEFAULT_RULE_TEXT_LIMIT = 2400


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_json(value, fallback):
    text = _to_text(value)
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _compact(text, limit=1200):
    text = _to_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def _rules_by_issue_type(rules_json_body):
    parsed = _parse_json(rules_json_body, {})
    if not isinstance(parsed, dict):
        return {}, "", []
    rules = parsed.get("rules")
    by_issue = {}
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            issue_type = _to_text(rule.get("issue_type"))
            if issue_type:
                by_issue[issue_type] = rule
    return by_issue, _to_text(parsed.get("version")), parsed.get("data_availability_rules") or []


def _get_nested_bool(payload, section, key):
    parsed = _parse_json(payload, {})
    if isinstance(parsed, dict):
        parent = parsed.get(section)
        if isinstance(parent, dict):
            return bool(parent.get(key))
        return bool(parsed.get(key))
    return False


def _get_is_aigc(aigc_attribute_panel):
    parsed = _parse_json(aigc_attribute_panel, {})
    if isinstance(parsed, dict):
        value = _to_text(parsed.get("is_AIGC")).lower()
        if value in {"true", "false"}:
            return value
    return "unknown"


def _get_cluster_types(comment_issue_clusters):
    parsed = _parse_json(comment_issue_clusters, {})
    if isinstance(parsed, dict):
        values = parsed.get("cluster_types")
        if isinstance(values, list):
            return {str(item).strip() for item in values if str(item).strip()}
    return set()


def _make_rule_section(rule):
    issue_type = _to_text(rule.get("issue_type"))
    name = _to_text(rule.get("name")) or issue_type
    lines = [f"Rule family: {issue_type}", f"Name: {name}"]

    for label, key in (
        ("Triggers", "triggers"),
        ("Required evidence", "required_evidence"),
        ("False positive boundaries", "false_positive_boundaries"),
    ):
        values = rule.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{label}:")
            for item in values[:8]:
                lines.append(f"- {item}")
    return "\n".join(lines)


def _append_family(selected, debug, rules_by_issue, issue_type, reason):
    if issue_type in selected:
        return
    rule = rules_by_issue.get(issue_type)
    if rule:
        selected[issue_type] = rule
        debug.append(f"{issue_type}: {reason}")


async def main(args: Args) -> Output:
    params = args.params

    rules_json_body = _to_text(params.get("rules_json_body"))
    rules_text_body = _to_text(params.get("rules_text_body"))
    video_signal_panel = _to_text(params.get("video_signal_panel"))
    aigc_attribute_panel = _to_text(params.get("aigc_attribute_panel"))
    product_identity_panel = _to_text(params.get("product_identity_panel"))
    comment_risk_summary = _to_text(params.get("comment_risk_summary"))
    comment_issue_clusters = _to_text(params.get("comment_issue_clusters"))

    rules_by_issue, rule_version, data_availability_rules = _rules_by_issue_type(rules_json_body)
    if not rules_by_issue:
        fallback = "\n".join([
            "PROJECT: LowqualityVideo",
            "RULE SOURCE MODE: fallback_text_rules",
            _compact(rules_text_body, DEFAULT_RULE_TEXT_LIMIT),
        ]).strip()
        ret = {
            "rules_context": fallback,
            "matched_rule_families": "fallback_text_rules",
            "rule_attention_debug": "structured rules JSON was missing or invalid; used rules_text_body fallback",
        }
        return ret

    selected = {}
    debug = []

    candidate_issue_map = {
        "only_marketing_sales_pitches": "only_marketing_sales_pitches",
        "out_of_app_transactions": "out_of_app_transactions",
        "misleading_functionality_and_effect": "misleading_functionality_and_effect",
        "potential_pirated_or_pirated": "potential_pirated",
        "non_native": "non_native",
        "disgusting_and_terrifying": "disgusting_and_terrifying",
        "pornography_perception": "pornography_perception",
        "dangerous_behavior": "dangerous_behavior",
        "unrealistic_or_continuity_error": "unrealistic_or_continuity_error",
    }

    for signal_key, issue_type in candidate_issue_map.items():
        if _get_nested_bool(video_signal_panel, "candidate_attention", signal_key):
            _append_family(
                selected,
                debug,
                rules_by_issue,
                issue_type,
                f"video_signal_panel candidate_attention.{signal_key}=true",
            )

    if _get_nested_bool(video_signal_panel, "candidate_attention", "potential_pirated_or_pirated"):
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "pirated_content",
            "pirated text signal should show both potential and confirmed piracy boundaries",
        )

    is_aigc = _get_is_aigc(aigc_attribute_panel)
    if is_aigc == "true":
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "unrealistic_or_continuity_error",
            "is_AIGC=true only boosts unrealistic_or_continuity_error attention",
        )

    product_identity = _parse_json(product_identity_panel, {})
    product_image_count = 0
    if isinstance(product_identity, dict):
        try:
            product_image_count = int(product_identity.get("product_image_count") or 0)
        except Exception:
            product_image_count = 0
    if product_image_count > 0:
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "inconsistent_product_promotion",
            "product images are available for displayed-vs-bound product comparison",
        )
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "no_physical_product_display",
            "product images are available to check whether video shows the actual physical product/package",
        )

    cluster_types = _get_cluster_types(comment_issue_clusters)
    comment_text = f"{comment_risk_summary}\n{comment_issue_clusters}".lower()

    if "pirated_or_reposted_claim" in cluster_types:
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "pirated_content",
            "comment cluster mentions copied/reposted content; comments are support only",
        )
        _append_family(
            selected,
            debug,
            rules_by_issue,
            "potential_pirated",
            "comment cluster mentions copied/reposted content; include high-threshold splicing boundaries",
        )
    if "out_of_app_transaction_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "out_of_app_transactions", "comment cluster mentions off-platform transaction")
    if "pornography_or_vulgar_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "pornography_perception", "comment cluster mentions vulgar or sexualized content")
    if "dangerous_behavior_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "dangerous_behavior", "comment cluster mentions dangerous behavior")
    if "misleading_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "misleading_functionality_and_effect", "comment cluster mentions misleading effect or fake ad")
    if "unrealistic_or_aigc_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "unrealistic_or_continuity_error", "comment cluster mentions AI/unrealistic content")
    if "no_physical_product_display_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "no_physical_product_display", "comment cluster mentions missing physical product")
    if "only_marketing_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "only_marketing_sales_pitches", "comment cluster mentions only marketing")
    if "non_native_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "non_native", "comment cluster mentions non-native style")
    if "disgusting_or_terrifying_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "disgusting_and_terrifying", "comment cluster mentions disgusting or terrifying content")
    if "irrelevant_promotion_claim" in cluster_types:
        _append_family(selected, debug, rules_by_issue, "irrelevant_promotion", "comment cluster mentions unrelated product promotion")

    if "product never appears" in comment_text or "no physical product" in comment_text:
        _append_family(selected, debug, rules_by_issue, "no_physical_product_display", "comment text mentions no physical product display")

    # Always include the most important ambiguity boundaries even when signals are sparse.
    for issue_type, reason in (
        ("potential_pirated", "baseline high-FP boundary for splicing/piracy"),
        ("pirated_content", "baseline high-FP boundary for confirmed non-original content"),
        ("irrelevant_promotion", "baseline product relevance check"),
        ("unrealistic_or_continuity_error", "baseline visual reality and continuity check"),
    ):
        _append_family(selected, debug, rules_by_issue, issue_type, reason)

    sections = [
        "PROJECT: LowqualityVideo",
        f"RULE_VERSION: {rule_version or 'unknown'}",
        "SCOPE: Use only the 15 in-scope issue types plus none. Do not cover the complete SOP.",
        "FRAME SAMPLING CONTRACT: frame_list contains up to 8 uniformly sampled frames; adjacent frames are sampled neighbors, not one second apart.",
        "IS_AIGC RULE: is_AIGC is an attribute only. is_AIGC=true only boosts unrealistic_or_continuity_error and never creates a hit by itself.",
        "PIRACY THRESHOLD: pirated_content and potential_pirated require strong internal evidence. Comments alone cannot hit pirated_content. Do not use external Pearl fields.",
    ]
    if data_availability_rules:
        sections.append("DATA AVAILABILITY RULES:")
        for rule in data_availability_rules:
            sections.append(f"- {rule}")

    sections.append("ACTIVE RULE FAMILIES:")
    for issue_type in sorted(selected):
        sections.append(_make_rule_section(selected[issue_type]))

    matched = sorted(selected.keys())
    ret = {
        "rules_context": "\n\n".join(sections),
        "matched_rule_families": ", ".join(matched),
        "rule_attention_debug": "\n".join(debug) if debug else "baseline rule families only",
    }
    return ret
