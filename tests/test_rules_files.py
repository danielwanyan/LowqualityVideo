import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_RULES = ROOT / "rules" / "lowquality_video_rules_structured_v1.json"
TEXT_RULES = ROOT / "rules" / "lowquality_video_rules_text_v1.txt"


EXPECTED_ISSUE_TYPES = {
    "video_product_mismatch",
    "misleading_functionality_or_effect",
    "suspected_pirated_or_reused_content",
    "pure_marketing_pitch",
    "no_physical_product_display",
    "irrelevant_product_promotion",
    "unrealistic_or_continuity_error",
    "sexual_or_vulgar_hook",
    "disgusting_or_terrifying_visual",
    "pirated_content",
    "description_not_detailed",
    "out_of_app_transaction",
    "still_frame",
}

EXPECTED_PRIORITY = [
    "suspected_pirated_or_reused_content",
    "misleading_functionality_or_effect",
    "unrealistic_or_continuity_error",
    "pure_marketing_pitch",
    "disgusting_or_terrifying_visual",
    "sexual_or_vulgar_hook",
    "description_not_detailed",
    "out_of_app_transaction",
    "pirated_content",
    "still_frame",
    "no_physical_product_display",
    "irrelevant_product_promotion",
    "video_product_mismatch",
    "none",
]


class LowqualityVideoRulesTest(unittest.TestCase):
    def load_rules(self):
        with STRUCTURED_RULES.open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_structured_rules_exist_and_cover_exact_issue_types(self):
        data = self.load_rules()

        actual = {rule["issue_type"] for rule in data["rules"]}

        self.assertEqual(data["version"], "2026-09-22-v6.1-smoke-calibration")
        self.assertEqual(actual, EXPECTED_ISSUE_TYPES)
        self.assertEqual(set(data["primary_issue_types"]), EXPECTED_ISSUE_TYPES | {"none"})
        self.assertEqual(data["primary_issue_types"], EXPECTED_PRIORITY)
        self.assertEqual(data["business_label_priority"], [
            "疑似盗版 / 疑似盗剪", "功能效果虚假夸大", "穿帮 / 不符现实", "仅营销叫卖",
            "恶心恐怖", "擦边低俗", "内容介绍不详细（低质）", "站外引流交易",
            "盗版内容", "静止帧", "无实物展示（围绕商品讲解）", "内容与商品无关推广",
            "挂车商品与讲解商品不一致", "无问题", "视频不可见",
        ])

    def test_evidence_contract_is_video_first(self):
        data = self.load_rules()

        self.assertEqual(
            data["evidence_contract"]["judgment_evidence"],
            ["frame_list", "ASR", "OCR", "images", "country"],
        )
        self.assertEqual(
            data["evidence_contract"]["display_only"],
            ["url", "product_id", "seller_id_str"],
        )
        self.assertEqual(data["decision_values"], ["problematic", "clean"])

    def test_removed_start_fields_are_absent_from_the_contract(self):
        data = self.load_rules()

        contract = data["evidence_contract"]
        serialized = json.dumps(contract, ensure_ascii=False)
        for removed_field in ("author_id", "comments", "product_review_summary"):
            self.assertNotIn(removed_field, serialized)

        for rule in data["rules"]:
            joined = " ".join(
                str(item)
                for key in ("triggers", "required_evidence")
                for item in rule.get(key, [])
            ).lower()
            self.assertNotIn("comment evidence", joined)
            self.assertNotIn("product_review_summary", joined)

    def test_piracy_rules_require_strong_video_internal_evidence(self):
        data = self.load_rules()
        rules_by_type = {rule["issue_type"]: rule for rule in data["rules"]}

        for issue_type in ("pirated_content", "suspected_pirated_or_reused_content"):
            rule = rules_by_type[issue_type]
            joined = " ".join(rule["false_positive_boundaries"] + rule["required_evidence"]).lower()
            self.assertIn("do not", joined)
            self.assertNotIn("product_review_summary", joined)

    def test_text_rules_include_core_boundaries(self):
        text = TEXT_RULES.read_text(encoding="utf-8")

        self.assertIn("LowqualityVideo Rules v6", text)
        self.assertIn("Allowed model evidence: frame_list, ASR, OCR, images, country", text)
        self.assertIn("Display-only fields: url, product_id, seller_id_str", text)
        self.assertNotIn("author_id", text)
        self.assertNotIn("comments", text)
        self.assertNotIn("product_review_summary", text)
        self.assertIn("Forbidden final decision: manual_review", text)
        self.assertIn("Forbidden output: tagsProduct", text)
        self.assertIn("color-only differences", text)
        self.assertIn("AI-generated style does not equal no physical product display", text)
        self.assertIn("is_aigc=1 is required", text)
        self.assertIn("If uncertain, choose clean", text)
        self.assertIn("pirated_content", text)
        self.assertIn("There are 15 business labels in total", text)
        self.assertIn("14. 无问题", text)
        self.assertIn("15. 视频不可见", text)

    def test_v5_false_positive_boundaries_from_599_eval_are_encoded(self):
        data = self.load_rules()
        by_type = {rule["issue_type"]: json.dumps(rule, ensure_ascii=False).lower() for rule in data["rules"]}
        text = TEXT_RULES.read_text(encoding="utf-8").lower()

        self.assertEqual(data["version"], "2026-09-22-v6.1-smoke-calibration")
        self.assertIn("商品图", by_type["misleading_functionality_or_effect"])
        self.assertIn("must be supported by frame_list, asr, or ocr", by_type["misleading_functionality_or_effect"])
        self.assertIn("商品详情页", text)
        self.assertIn("color-only", by_type["video_product_mismatch"])
        self.assertIn("brand text", by_type["video_product_mismatch"])
        self.assertIn("replying to a user comment", by_type["suspected_pirated_or_reused_content"])
        self.assertIn("self-verifying", by_type["suspected_pirated_or_reused_content"])
        self.assertIn("angle shift", by_type["still_frame"])
        self.assertIn("lighting shift", by_type["still_frame"])
        self.assertIn("directly taking an item from a sealed or unopened package", by_type["unrealistic_or_continuity_error"])
        self.assertIn("connector, plug, hook, screw, support bar, or mounting structure", by_type["unrealistic_or_continuity_error"])

    def test_reviewed_gt_boundaries_are_encoded(self):
        data = self.load_rules()
        by_type = {rule["issue_type"]: json.dumps(rule, ensure_ascii=False).lower() for rule in data["rules"]}
        self.assertIn("materially stronger than the bound product", by_type["misleading_functionality_or_effect"])
        self.assertIn("ordinary speech error", by_type["misleading_functionality_or_effect"])
        self.assertIn("wearing", by_type["pure_marketing_pitch"])
        self.assertIn("real product use", by_type["pure_marketing_pitch"])
        self.assertIn("visible package", by_type["no_physical_product_display"])
        self.assertIn("approximately one third", by_type["irrelevant_product_promotion"])
        self.assertIn("is_aigc=1 is required", by_type["unrealistic_or_continuity_error"])
        self.assertIn("is_aigc is not piracy evidence", by_type["suspected_pirated_or_reused_content"])
        self.assertIn("ordinary b-roll", by_type["suspected_pirated_or_reused_content"])
        self.assertIn("source-authenticity", by_type["suspected_pirated_or_reused_content"])
        self.assertIn("irrelevant_product_promotion", by_type["no_physical_product_display"])
        self.assertIn("finger", by_type["unrealistic_or_continuity_error"])
        self.assertIn("viscous", by_type["disgusting_or_terrifying_visual"])
        self.assertIn("product name and package", by_type["description_not_detailed"])
        self.assertIn("static-image sequence", by_type["still_frame"])


if __name__ == "__main__":
    unittest.main()
