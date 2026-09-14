import asyncio
import json
import unittest
from pathlib import Path

from code_nodes import rules_brain


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_RULES = ROOT / "rules" / "lowquality_video_rules_structured_v1.json"
TEXT_RULES = ROOT / "rules" / "lowquality_video_rules_text_v1.txt"


class DummyArgs:
    def __init__(self, params):
        self.params = params


class RulesBrainTest(unittest.TestCase):
    def run_node(self, params):
        base = {
            "rules_json_body": STRUCTURED_RULES.read_text(encoding="utf-8"),
            "rules_text_body": TEXT_RULES.read_text(encoding="utf-8"),
            "video_signal_panel": "{}",
            "aigc_attribute_panel": "{}",
            "product_identity_panel": "{}",
        }
        base.update(params)
        return asyncio.run(rules_brain.main(DummyArgs(base)))

    def test_selects_hard_sell_and_off_platform_rules_from_video_signals(self):
        result = self.run_node({
            "video_signal_panel": json.dumps({
                "candidate_attention": {
                    "only_marketing_sales_pitches": True,
                    "out_of_app_transactions": True,
                }
            }),
        })

        families = result["matched_rule_families"].split(", ")
        self.assertIn("only_marketing_sales_pitches", families)
        self.assertIn("out_of_app_transactions", families)
        self.assertIn("Only hard-sell marketing pitches", result["rules_context"])
        self.assertIn("Off-platform transaction guidance", result["rules_context"])

    def test_is_aigc_true_only_adds_unrealistic_attention(self):
        result = self.run_node({
            "aigc_attribute_panel": json.dumps({"is_AIGC": "true"}),
        })

        families = result["matched_rule_families"].split(", ")
        self.assertIn("unrealistic_or_continuity_error", families)
        self.assertNotIn("misleading_functionality_and_effect", families)
        self.assertNotIn("no_physical_product_display", families)
        self.assertIn("is_AIGC=true only boosts unrealistic_or_continuity_error", result["rule_attention_debug"])

    def test_comment_inputs_are_ignored_even_if_provided(self):
        result = self.run_node({
            "comment_risk_summary": "COMMENT_SIGNAL_STRENGTH: strong",
            "comment_issue_clusters": json.dumps({
                "cluster_types": ["pirated_or_reposted_claim"],
                "clusters": {
                    "pirated_or_reposted_claim": [
                        {"source": "comment_text", "evidence": "stolen from original creator"}
                    ]
                },
            }),
        })

        families = result["matched_rule_families"].split(", ")
        self.assertIn("pirated_content", families)
        self.assertIn("potential_pirated", families)
        self.assertNotIn("comment cluster", result["rule_attention_debug"])
        self.assertIn("baseline high-FP boundary", result["rule_attention_debug"])
        self.assertIn("Use no review/commentary inputs and no external Pearl fields", result["rules_context"])
        self.assertNotIn("stolen from original creator", result["rules_context"])

    def test_falls_back_to_text_rules_when_structured_json_missing(self):
        result = self.run_node({
            "rules_json_body": "",
            "rules_text_body": "LowqualityVideo Rules v2\nDo not use external Pearl fields.",
        })

        self.assertIn("LowqualityVideo Rules v2", result["rules_context"])
        self.assertIn("fallback_text_rules", result["matched_rule_families"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({})

        self.assertEqual(set(result.keys()), {
            "rules_context",
            "matched_rule_families",
            "rule_attention_debug",
        })


if __name__ == "__main__":
    unittest.main()
