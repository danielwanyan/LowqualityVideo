import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT = ROOT / "prompts" / "sop_multimodal_risk_reviewer_system_prompt.txt"
USER_PROMPT = ROOT / "prompts" / "sop_multimodal_risk_reviewer_user_prompt.txt"


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
    "none",
]


class PromptFilesTest(unittest.TestCase):
    def test_system_prompt_is_plain_text_without_template_variables(self):
        text = SYSTEM_PROMPT.read_text(encoding="utf-8")

        self.assertNotIn("{{", text)
        self.assertNotIn("}}", text)
        self.assertNotIn("```", text)
        self.assertNotIn("# ", text)
        self.assertIn("System Prompt must stay plain text", text)
        self.assertIn("is_AIGC only increases attention for unrealistic_or_continuity_error", text)

    def test_user_prompt_contains_required_variables(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        required_variables = [
            "{{gated_all_image_urls}}",
            "{{gated_all_image_manifest}}",
            "{{gated_risk_attention_packet}}",
            "{{evidence_gate_panel}}",
            "{{allowed_issue_types}}",
            "{{forbidden_claims}}",
            "{{recommended_decision_floor}}",
            "{{video_id}}",
            "{{product_id}}",
            "{{country}}",
            "{{seller_id_str}}",
            "{{is_AIGC}}",
            "{{ASR}}",
            "{{OCR}}",
        ]
        for variable in required_variables:
            self.assertIn(variable, text)

        self.assertNotIn("{{comments}}", text)
        self.assertNotIn("{{product_review_summary}}", text)

    def test_user_prompt_lists_only_allowed_issue_types(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        for issue in ALLOWED_ISSUES:
            self.assertIn(issue, text)
        forbidden_legacy = [
            "video_product_mismatch",
            "video_exaggerated_promotion",
            "race_conflict_or_fake_police",
            "staged_mass_production_or_pure_marketing",
            "ipr_or_counterfeit",
            "poor_product_quality",
            "product_side_mismatch_or_exaggeration",
        ]
        for issue in forbidden_legacy:
            self.assertNotIn(issue, text)

    def test_user_prompt_requires_raw_json_and_chinese_evidence(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        self.assertIn("Return raw JSON only", text)
        self.assertIn("All summaries, reasons, and evidence fields must be in Chinese", text)
        self.assertIn("Use only video frames, ASR, OCR, and product evidence for analysis", text)


if __name__ == "__main__":
    unittest.main()
