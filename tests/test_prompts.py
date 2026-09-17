import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT = ROOT / "prompts" / "sop_multimodal_risk_reviewer_system_prompt.txt"
USER_PROMPT = ROOT / "prompts" / "sop_multimodal_risk_reviewer_user_prompt.txt"


ALLOWED_ISSUES = [
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
    "none",
]


class PromptFilesTest(unittest.TestCase):
    def test_system_prompt_is_plain_text_without_template_variables(self):
        text = SYSTEM_PROMPT.read_text(encoding="utf-8")

        self.assertNotIn("{{", text)
        self.assertNotIn("}}", text)
        self.assertNotIn("```", text)
        self.assertNotIn("# ", text)
        self.assertIn("Allowed judgment evidence is limited to frame_list, ASR, OCR, product images, and country.", text)
        self.assertIn("Do not output product-side labels.", text)

    def test_user_prompt_contains_required_variables(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        required_variables = [
            "{{gated_all_image_urls}}",
            "{{gated_all_image_manifest}}",
            "{{final_reviewer_context}}",
            "{{evidence_gate_panel}}",
            "{{allowed_issue_types}}",
            "{{forbidden_claims}}",
            "{{video_id}}",
            "{{country}}",
            "{{ASR}}",
            "{{OCR}}",
        ]
        for variable in required_variables:
            self.assertIn(variable, text)

        self.assertNotIn("{{comments}}", text)
        self.assertNotIn("{{product_review_summary}}", text)
        self.assertNotIn("{{product_id}}", text)
        self.assertNotIn("{{seller_id_str}}", text)
        self.assertNotIn("{{is_AIGC}}", text)

    def test_user_prompt_lists_only_allowed_issue_types(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        for issue in ALLOWED_ISSUES:
            self.assertIn(issue, text)
        forbidden_legacy = [
            "video_exaggerated_promotion",
            "race_conflict_or_fake_police",
            "staged_mass_production_or_pure_marketing",
            "ipr_or_counterfeit",
            "poor_product_quality",
            "product_side_mismatch_or_exaggeration",
            "inconsistent_product_promotion",
            "misleading_functionality_and_effect",
            "only_marketing_sales_pitches",
            "potential_pirated",
        ]
        for issue in forbidden_legacy:
            self.assertNotIn(issue, text)

    def test_user_prompt_requires_raw_json_and_chinese_evidence(self):
        text = USER_PROMPT.read_text(encoding="utf-8")

        self.assertIn("Return raw JSON only", text)
        self.assertIn("All summaries, reasons, and evidence fields must be in Chinese", text)
        self.assertIn("Use frame_list, ASR, and OCR as primary video evidence", text)


if __name__ == "__main__":
    unittest.main()
