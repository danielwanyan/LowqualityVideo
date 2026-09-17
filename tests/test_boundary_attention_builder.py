import asyncio
import json
import unittest

from code_nodes import boundary_attention_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class BoundaryAttentionBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(boundary_attention_builder.main(DummyArgs(params)))

    def test_excludes_display_only_fields_even_if_provided(self):
        result = self.run_node({
            "video_text_panel": json.dumps({
                "asr_text": "Only today, buy now, huge discount",
                "ocr_text": "",
                "signals": {
                    "has_hard_sell_terms": True,
                    "has_substantive_product_terms": False,
                    "has_misleading_terms": False,
                    "has_pirated_terms": False,
                },
            }, ensure_ascii=False),
            "video_data_quality_json": json.dumps({
                "video_frames_available": True,
                "asr_available": True,
                "ocr_available": False,
            }, ensure_ascii=False),
            "product_aux_panel": "COUNTRY: ES\nPRODUCT_IMAGE_COUNT: 1",
            "product_aux_data_quality_json": json.dumps({
                "product_images_available": True,
                "country_available": True,
            }, ensure_ascii=False),
            "rules_json_body": "{}",
            "comments": "must-not-appear",
            "product_review_summary": "must-not-appear",
            "product_id": "must-not-appear",
            "seller_id_str": "must-not-appear",
        })

        self.assertIn("pure_marketing_pitch", result["active_boundary_groups"])
        joined = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("must-not-appear", joined)
        self.assertNotIn("product_review_summary", joined)
        self.assertNotIn("comments", joined)

    def test_continuity_boundary_is_low_priority_and_clean_when_uncertain(self):
        result = self.run_node({
            "video_text_panel": json.dumps({
                "signals": {
                    "has_hard_sell_terms": False,
                    "has_substantive_product_terms": False,
                    "has_misleading_terms": False,
                    "has_pirated_terms": False,
                }
            }, ensure_ascii=False),
            "video_data_quality_json": json.dumps({
                "video_frames_available": True,
                "asr_available": False,
                "ocr_available": False,
            }, ensure_ascii=False),
            "product_aux_panel": "COUNTRY: FR\nPRODUCT_IMAGE_COUNT: 1",
            "product_aux_data_quality_json": json.dumps({
                "product_images_available": True,
                "country_available": True,
            }, ensure_ascii=False),
            "rules_json_body": "{}",
        })

        self.assertIn("unrealistic_or_continuity_error", result["active_boundary_groups"])
        self.assertIn("lower priority", result["boundary_attention_packet"])
        self.assertIn("If uncertain, choose clean", result["boundary_attention_packet"])

    def test_uses_structured_rule_json_when_available(self):
        rules_json_body = json.dumps({
            "version": "test-v4",
            "rules": [{
                "issue_type": "video_product_mismatch",
                "label": "挂车商品与讲解商品不一致",
                "triggers": ["CUSTOM_RULE_TRIGGER"],
                "false_positive_boundaries": ["CUSTOM_RULE_BOUNDARY"],
                "required_evidence": ["CUSTOM_RULE_EVIDENCE"],
            }],
        }, ensure_ascii=False)

        result = self.run_node({
            "video_text_panel": json.dumps({"signals": {}}, ensure_ascii=False),
            "video_data_quality_json": json.dumps({
                "video_frames_available": True,
                "asr_available": False,
                "ocr_available": False,
            }, ensure_ascii=False),
            "product_aux_panel": "COUNTRY: ES\nPRODUCT_IMAGE_COUNT: 1",
            "product_aux_data_quality_json": json.dumps({
                "product_images_available": True,
                "country_available": True,
            }, ensure_ascii=False),
            "rules_json_body": rules_json_body,
        })

        self.assertIn("RULE_VERSION: test-v4", result["boundary_attention_packet"])
        self.assertIn("CUSTOM_RULE_TRIGGER", result["boundary_attention_packet"])
        self.assertIn("CUSTOM_RULE_BOUNDARY", result["boundary_attention_packet"])
        self.assertIn("CUSTOM_RULE_EVIDENCE", result["boundary_attention_packet"])


if __name__ == "__main__":
    unittest.main()
