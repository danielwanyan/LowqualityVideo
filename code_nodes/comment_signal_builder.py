import json
import re


COMMENT_LINE_RE = re.compile(r"^\[(\d+)\]\s+ccr_list:\s*(.*?)\s*\|\s*text:\s*(.*)$")


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_comments(comments):
    raw = _to_text(comments)
    if not raw:
        return []

    parsed = []
    for line_index, line in enumerate(re.split(r"[\r\n]+", raw)):
        line = line.strip()
        if not line:
            continue
        match = COMMENT_LINE_RE.match(line)
        if match:
            ccr_raw = match.group(2).strip()
            ccr_tags = []
            if ccr_raw:
                for part in re.split(r"[,;]", ccr_raw):
                    tag = part.strip().strip('"').strip()
                    if tag:
                        ccr_tags.append(tag)
            parsed.append({
                "comment_index": int(match.group(1)),
                "ccr_tags": ccr_tags,
                "text": match.group(3).strip(),
                "format": "ccr_line",
            })
        else:
            parsed.append({
                "comment_index": line_index,
                "ccr_tags": [],
                "text": line,
                "format": "plain_line",
            })
    return parsed


def _add_cluster(clusters, cluster_type, source, evidence):
    evidence = _to_text(evidence)
    if not evidence:
        return
    if cluster_type not in clusters:
        clusters[cluster_type] = []
    item = {
        "source": source,
        "evidence": evidence[:500],
    }
    if item not in clusters[cluster_type]:
        clusters[cluster_type].append(item)


def _has_any(text, keywords):
    lowered = _to_text(text).lower()
    return any(keyword in lowered for keyword in keywords)


def _map_ccr_tag(tag):
    tag = _to_text(tag)
    lowered = tag.lower()
    if "copied" in lowered or "pirated" in lowered or "repost" in lowered:
        return "pirated_or_reposted_claim"
    if "offplatform" in lowered or "transaction" in lowered:
        return "out_of_app_transaction_claim"
    if "vulgar" in lowered or "sexual" in lowered or "porn" in lowered:
        return "pornography_or_vulgar_claim"
    if "danger" in lowered or "safety" in lowered:
        return "dangerous_behavior_claim"
    if "misleading" in lowered:
        return "misleading_claim"
    if "artificialintelligencegeneratedcontent" in lowered or "aigc" in lowered:
        return "unrealistic_or_aigc_claim"
    return ""


def _scan_text_for_clusters(text, source, clusters):
    value = _to_text(text)
    lowered = value.lower()
    if not lowered:
        return

    keyword_map = {
        "pirated_or_reposted_claim": [
            "stolen", "repost", "reposted", "copied", "copy", "original creator",
            "watermark", "douyin", "搬运", "盗用", "盗播", "转载", "原作者", "抖音", "水印",
        ],
        "out_of_app_transaction_claim": [
            "paypal", "venmo", "cash app", "cashapp", "zelle", "whatsapp",
            "telegram", "phone number", "call me", "text me", "dm me to buy",
            "link in bio", "website", "bank transfer", "站外", "微信", "支付宝", "私信购买",
        ],
        "misleading_claim": [
            "fake ad", "misleading", "scam", "not like the video", "doesn't work",
            "does not work", "fake ai", "over edited", "夸大", "虚假", "骗人", "诈骗",
        ],
        "unrealistic_or_aigc_claim": [
            " ai ", "aigc", "artificial intelligence", "generated", "cgi",
            "not real", "unreal", "fake ai", "不真实", "ai生成", "生成的",
        ],
        "no_physical_product_display_claim": [
            "product never appears", "no product", "only picture", "screenshot",
            "just a photo", "no real product", "没有实物", "无实物", "只有图片",
        ],
        "only_marketing_claim": [
            "buy now", "add to cart", "discount ends", "sale ends", "only says buy",
            "just selling", "hard sell", "下单", "优惠", "折扣", "库存", "只会叫卖",
        ],
        "non_native_claim": [
            "chinese text", "bad english", "chinglish", "can't understand",
            "中文", "看不懂", "中式英语",
        ],
        "disgusting_or_terrifying_claim": [
            "disgusting", "gross", "terrifying", "scary", "scream", "dirty",
            "insect", "cockroach", "sewer", "恶心", "恐怖", "尖叫", "昆虫", "下水道",
        ],
        "pornography_or_vulgar_claim": [
            "sexy", "sexual", "vulgar", "cleavage", "underwear", "lingerie",
            "spend the night", "擦边", "低俗", "性暗示", "内衣", "过夜",
        ],
        "dangerous_behavior_claim": [
            "dangerous", "unsafe", "fire", "smoke", "explosion", "knife",
            "危险", "不安全", "火", "烟", "爆炸", "刀",
        ],
        "irrelevant_promotion_claim": [
            "unrelated", "nothing to do with product", "not about the product",
            "内容无关", "和商品无关", "不相关",
        ],
    }

    padded = f" {lowered} "
    for cluster_type, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in padded or keyword in lowered:
                _add_cluster(clusters, cluster_type, source, value)
                break


def _cluster_strength(clusters):
    if not clusters:
        return "none"
    evidence_count = sum(len(items) for items in clusters.values())
    high_risk_clusters = {
        "pirated_or_reposted_claim",
        "out_of_app_transaction_claim",
        "pornography_or_vulgar_claim",
        "dangerous_behavior_claim",
        "misleading_claim",
    }
    high_risk_count = sum(1 for key in clusters if key in high_risk_clusters)
    if evidence_count >= 4 or high_risk_count >= 2:
        return "strong"
    if evidence_count >= 2 or high_risk_count == 1:
        return "medium"
    return "weak"


def _representative_quotes(clusters, limit=8):
    quotes = []
    for cluster_type in sorted(clusters):
        for item in clusters[cluster_type]:
            quotes.append(f"{cluster_type}: {item['evidence']}")
            if len(quotes) >= limit:
                return quotes
    return quotes


async def main(args: Args) -> Output:
    params = args.params

    comments = _to_text(params.get("comments"))
    product_review_summary = _to_text(params.get("product_review_summary"))
    product_id = _to_text(params.get("product_id"))

    parsed_comments = _parse_comments(comments)
    clusters = {}

    for comment in parsed_comments:
        text = comment.get("text", "")
        for tag in comment.get("ccr_tags", []):
            cluster_type = _map_ccr_tag(tag)
            if cluster_type:
                _add_cluster(clusters, cluster_type, f"comment_ccr:{tag}", text or tag)
        _scan_text_for_clusters(text, "comment_text", clusters)

    _scan_text_for_clusters(product_review_summary, "product_review_summary", clusters)

    cluster_types = sorted(clusters.keys())
    strength = _cluster_strength(clusters)
    quotes = _representative_quotes(clusters)

    cluster_payload = {
        "product_id": product_id,
        "cluster_types": cluster_types,
        "clusters": clusters,
        "comment_count": len(parsed_comments),
        "meaningful_comment_count": sum(1 for comment in parsed_comments if comment.get("text")),
        "rules": [
            "Comments are supporting signals only.",
            "Comments alone cannot hit pirated_content or potential_pirated.",
            "For pirated labels, require frame or ASR/OCR evidence in addition to comments.",
            "Do not introduce product quality labels outside the 15-label LowqualityVideo scope.",
        ],
    }

    warnings = []
    if not comments:
        warnings.append("comments is empty")
    if not product_review_summary:
        warnings.append("product_review_summary is empty")

    data_quality = {
        "comments_available": bool(comments),
        "parsed_comment_count": len(parsed_comments),
        "meaningful_comment_count": sum(1 for comment in parsed_comments if comment.get("text")),
        "product_review_summary_available": bool(product_review_summary),
        "warnings": warnings,
    }

    summary_lines = [
        f"PRODUCT_ID: {product_id}",
        f"COMMENT_SIGNAL_STRENGTH: {strength}",
        f"CLUSTER_TYPES: {', '.join(cluster_types) if cluster_types else 'none'}",
        f"PARSED_COMMENT_COUNT: {len(parsed_comments)}",
        f"MEANINGFUL_COMMENT_COUNT: {data_quality['meaningful_comment_count']}",
        "Comments are supporting signals only; they do not create final issue hits by themselves.",
    ]

    ret = {
        "comment_risk_summary": "\n".join(summary_lines),
        "comment_issue_clusters": json.dumps(cluster_payload, ensure_ascii=False),
        "representative_comment_quotes": "\n".join(quotes),
        "comment_data_quality": json.dumps(data_quality, ensure_ascii=False),
    }
    return ret
