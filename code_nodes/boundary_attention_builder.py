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


def _bool(data, key):
    return bool(data.get(key))


def _compact(text, limit=1400):
    text = _to_text(text)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def _signals(video_text_panel):
    parsed = _json_dict(video_text_panel)
    signals = parsed.get("signals")
    return signals if isinstance(signals, dict) else {}


def _rules_by_issue_type(rules_json_body):
    parsed = _json_dict(rules_json_body)
    rules = parsed.get("rules")
    if not isinstance(rules, list):
        return {}, ""
    by_issue = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        issue_type = _to_text(rule.get("issue_type"))
        if issue_type:
            by_issue[issue_type] = rule
    return by_issue, _to_text(parsed.get("version"))


BOUNDARIES = {
    "video_product_mismatch": {
        "title": "IPP / 挂车商品与讲解商品不一致",
        "must_not_infer": [
            "不要把颜色、轻微材质、包装语言、普通品牌文字差异当成挂车商品不一致。",
            "不要因为视频展示数量多于商品图就直接判断不一致，除非售卖承诺明确冲突。",
        ],
        "positive_hit_tests": [
            "只有视频主商品与商品图核心品类、功能、形态、数量、关键规格或承诺用途明显冲突时才命中。",
        ],
    },
    "misleading_functionality_or_effect": {
        "title": "MFE / 功能效果虚假夸大",
        "must_not_infer": [
            "不要用商品图单独判定视频夸大。",
            "不要把普通广告语、主观好评、比喻、服饰显身材、正常清洁/剃须/造型效果当成夸大。",
        ],
        "positive_hit_tests": [
            "视频帧、ASR 或 OCR 明确承诺功效、速度、持续时间、医疗健康效果、数量、前后对比、安全或物理能力，且该承诺明显误导时才命中。",
        ],
    },
    "suspected_pirated_or_reused_content": {
        "title": "疑似盗版 / 疑似盗剪",
        "must_not_infer": [
            "不要把回复网友、自证效果、展示其他博主后自己验证、同一达人换场景讲解直接当成盗播。",
        ],
        "positive_hit_tests": [
            "明显中国录播/国内工作室环境、中文界面、不符合目标市场语境、模糊搬运、遮水印三明治结构或明显复用无关创作者内容时才命中。",
        ],
    },
    "no_physical_product_display": {
        "title": "无实物展示（围绕商品讲解）",
        "must_not_infer": [
            "AI 生成风格不等于无实物展示。",
            "只要视频清晰展示挂车商品或核心使用场景，就不要命中无实物展示。",
        ],
        "positive_hit_tests": [
            "视频围绕商品讲解但始终没有展示商品实物或核心使用场景时才命中。",
        ],
    },
    "still_frame": {
        "title": "静止帧",
        "must_not_infer": [
            "不要把有角度变化、光影变化、姿态变化、相机移动或商品移动的视频当成静止帧。",
        ],
        "positive_hit_tests": [
            "采样帧几乎完全静止且没有实质商品演示时才命中。",
        ],
    },
    "pure_marketing_pitch": {
        "title": "仅营销叫卖",
        "must_not_infer": [
            "不要把弱但真实的产品功能、材质、尺寸、使用场景或操作方法讲解判成仅营销叫卖。",
        ],
        "positive_hit_tests": [
            "ASR/OCR 几乎全是价格、库存、折扣、催单和购买引导，且几乎没有真实商品信息时才命中。",
        ],
    },
    "irrelevant_product_promotion": {
        "title": "内容与商品无关推广",
        "must_not_infer": [
            "不要因为开头铺垫或短暂无关片段就命中无关推广。",
        ],
        "positive_hit_tests": [
            "视频主体大部分与挂车商品无关，商品只在末尾短暂出现或没有实质展示时才命中。",
        ],
    },
    "unrealistic_or_continuity_error": {
        "title": "穿帮 / 不符现实",
        "must_not_infer": [
            "This label is lower priority than IPP, MFE, suspected pirated/reused content, no-product display, and pure marketing because the workflow only receives up to 8 sampled frames.",
            "不要因为抽样帧之间缺少中间动作、轻微手部伪影、光影角度变化、运动模糊或普通剪辑跳跃就命中。",
        ],
        "positive_hit_tests": [
            "只有强视觉证据、影响商品理解、且不能被抽样间隔/正常剪辑/视角切换解释的不现实变化才命中。",
            "If uncertain, choose clean.",
        ],
    },
    "sexual_or_vulgar_hook": {
        "title": "擦边低俗",
        "must_not_infer": [
            "不要把普通试穿、健身、泳装、塑身衣或身体展示当成擦边。",
        ],
        "positive_hit_tests": [
            "存在明确低俗钩子、成人暗示或以性暗示促销时才命中。",
        ],
    },
    "disgusting_or_terrifying_visual": {
        "title": "恶心恐怖",
        "must_not_infer": [
            "轻微不美观或普通产品问题不是恶心恐怖。",
        ],
        "positive_hit_tests": [
            "画面主体带来强烈不适、密集恐惧、伤害、污秽、身体或恐怖视觉时才命中。",
        ],
    },
    "out_of_app_transaction": {
        "title": "站外引流交易",
        "must_not_infer": [
            "TikTok 站内购买引导或单纯私信不算站外引流。",
        ],
        "positive_hit_tests": [
            "明确外部网址、二维码、站外平台或站外交易指令时才命中。",
        ],
    },
    "pirated_content": {
        "title": "盗版内容",
        "must_not_infer": [
            "不要把引用片段、回复评论语境或同一达人多场景剪辑直接当成盗版内容。",
        ],
        "positive_hit_tests": [
            "视频主体明确使用盗版版权内容进行商品推广时才命中。",
        ],
    },
    "description_not_detailed": {
        "title": "内容介绍不详细（低质）",
        "must_not_infer": [
            "服饰、简单商品或视觉商品只要清晰展示商品，不要因为口播少就判内容介绍不详细。",
        ],
        "positive_hit_tests": [
            "保健品、电器、工具等需要功能或用法说明的类目，如果画面、ASR、OCR 都没有有意义的商品信息，才命中。",
        ],
    },
}


def _boundary_for_group(group, rules_by_issue):
    fallback = BOUNDARIES[group]
    rule = rules_by_issue.get(group)
    if not isinstance(rule, dict):
        return fallback

    positive_tests = []
    for key in ("triggers", "required_evidence"):
        value = rule.get(key)
        if isinstance(value, list):
            positive_tests.extend(str(item) for item in value if str(item).strip())

    must_not = []
    value = rule.get("false_positive_boundaries")
    if isinstance(value, list):
        must_not.extend(str(item) for item in value if str(item).strip())

    return {
        "title": _to_text(rule.get("label")) or fallback["title"],
        "must_not_infer": must_not or fallback["must_not_infer"],
        "positive_hit_tests": positive_tests or fallback["positive_hit_tests"],
    }


def _active_groups(signals, video_quality, product_quality):
    groups = []
    has_frames = _bool(video_quality, "video_frames_available")
    has_product_images = _bool(product_quality, "product_images_available")
    has_text = _bool(video_quality, "asr_available") or _bool(video_quality, "ocr_available")

    if has_frames and has_product_images:
        groups.append("video_product_mismatch")
    if has_frames or has_text:
        groups.extend([
            "misleading_functionality_or_effect",
            "suspected_pirated_or_reused_content",
            "no_physical_product_display",
            "irrelevant_product_promotion",
            "unrealistic_or_continuity_error",
            "sexual_or_vulgar_hook",
            "disgusting_or_terrifying_visual",
            "pirated_content",
            "description_not_detailed",
        ])
    if has_text and signals.get("has_hard_sell_terms"):
        groups.append("pure_marketing_pitch")
        groups.append("out_of_app_transaction")
    if has_frames:
        groups.append("still_frame")

    deduped = []
    for group in groups:
        if group not in deduped:
            deduped.append(group)
    return deduped


async def main(args: Args) -> Output:
    params = args.params

    rules_json_body = _to_text(params.get("rules_json_body"))
    video_text_panel = _to_text(params.get("video_text_panel"))
    video_quality = _json_dict(params.get("video_data_quality_json") or params.get("video_data_quality"))
    product_aux_panel = _to_text(params.get("product_aux_panel"))
    product_quality = _json_dict(params.get("product_aux_data_quality_json"))

    signals = _signals(video_text_panel)
    active = _active_groups(signals, video_quality, product_quality)
    rules_by_issue, rule_version = _rules_by_issue_type(rules_json_body)

    must_not = []
    positive_tests = []
    sections = [
        "PROJECT: LowqualityVideo",
        f"RULE_VERSION: {rule_version or 'fallback-boundaries'}",
        "TASK: Video-first low-quality binary review.",
        "Allowed final decisions: problematic, clean.",
        "Forbidden final decision: manual review.",
        "Only these fields are judgment evidence: frame_list, ASR, OCR, images, country.",
        "Do not use display-only fields as judgment evidence.",
        f"VIDEO_TEXT_PANEL:\n{_compact(video_text_panel, 1800)}",
        f"PRODUCT_AUX_PANEL:\n{_compact(product_aux_panel, 1200)}",
    ]

    for group in active:
        boundary = _boundary_for_group(group, rules_by_issue)
        must_not.extend(boundary["must_not_infer"])
        positive_tests.extend(boundary["positive_hit_tests"])
        sections.append(
            "\n".join([
                f"BOUNDARY: {group} / {boundary['title']}",
                "Do not infer:",
                *[f"- {item}" for item in boundary["must_not_infer"]],
                "Positive hit tests:",
                *[f"- {item}" for item in boundary["positive_hit_tests"]],
            ])
        )

    return {
        "boundary_attention_packet": "\n\n".join(sections),
        "active_boundary_groups": ", ".join(active),
        "must_not_infer": "\n".join(f"- {item}" for item in must_not),
        "positive_hit_tests": "\n".join(f"- {item}" for item in positive_tests),
        "allowed_issue_types": ", ".join(BOUNDARIES.keys()) + ", none",
    }
