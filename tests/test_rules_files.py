import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_RULES = ROOT / "rules" / "lowquality_video_rules_structured_v1.json"
TEXT_RULES = ROOT / "rules" / "lowquality_video_rules_text_v1.txt"


EXPECTED_ISSUE_TYPES = {
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
}


class LowqualityVideoRulesTest(unittest.TestCase):
    def load_rules(self):
        with STRUCTURED_RULES.open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_structured_rules_exist_and_cover_exact_issue_types(self):
        data = self.load_rules()

        actual = {rule["issue_type"] for rule in data["rules"]}

        self.assertEqual(actual, EXPECTED_ISSUE_TYPES)
        self.assertEqual(
            data["primary_issue_types"],
            sorted(EXPECTED_ISSUE_TYPES) + ["none"],
        )

    def test_is_aigc_attention_only_targets_unrealistic_or_continuity(self):
        data = self.load_rules()

        attention = data["is_AIGC_usage"]["attention_boost_issue_types"]

        self.assertEqual(attention, ["unrealistic_or_continuity_error"])
        self.assertIn("must_not_trigger_issue_by_itself", data["is_AIGC_usage"])

    def test_piracy_rules_require_strong_internal_evidence(self):
        data = self.load_rules()
        rules_by_type = {rule["issue_type"]: rule for rule in data["rules"]}

        for issue_type in ("pirated_content", "potential_pirated"):
            rule = rules_by_type[issue_type]
            joined = " ".join(rule["false_positive_boundaries"] + rule["required_evidence"]).lower()
            self.assertIn("strong", joined)
            self.assertIn("do not", joined)
            self.assertIn("external", joined)

    def test_text_rules_include_core_boundaries(self):
        text = TEXT_RULES.read_text(encoding="utf-8")

        self.assertIn("LowqualityVideo Rules v1", text)
        self.assertIn("is_AIGC only increases attention for unrealistic_or_continuity_error", text)
        self.assertIn("Do not use external Pearl fields", text)
        self.assertIn("potential_pirated", text)
        self.assertIn("pirated_content", text)


if __name__ == "__main__":
    unittest.main()
