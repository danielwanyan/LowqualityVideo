import asyncio
import json
import unittest

from code_nodes import context_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class ContextBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(context_builder.main(DummyArgs(params)))

    def test_combines_product_images_before_video_frames(self):
        result = self.run_node({
            "video_frame_urls": ["https://cdn.example.com/f1.jpg", "https://cdn.example.com/f2.jpg"],
            "product_image_urls": ["https://cdn.example.com/p1.jpg"],
            "video_frame_manifest": "VIDEO_FRAME 001 | f1\nVIDEO_FRAME 002 | f2",
            "video_text_panel": json.dumps({"asr_text": "buy now"}),
            "aigc_attribute_panel": json.dumps({"is_AIGC": "false"}),
            "video_signal_panel": json.dumps({"signals": {"has_hard_sell_terms": True}}),
            "video_data_quality": json.dumps({"video_frames_available": True, "asr_available": True, "ocr_available": False}),
            "product_image_manifest": "PRODUCT_IMAGE 001 | p1",
            "product_identity_panel": json.dumps({"product_id": "p1", "product_image_count": 1}),
            "product_data_quality": json.dumps({"product_images_available": True}),
            "comment_risk_summary": "COMMENT_SIGNAL_STRENGTH: none",
            "comment_issue_clusters": json.dumps({"cluster_types": []}),
            "representative_comment_quotes": "",
            "comment_data_quality": json.dumps({"comments_available": False}),
            "rules_context": "PROJECT: LowqualityVideo\nRule family: only_marketing_sales_pitches",
            "matched_rule_families": "only_marketing_sales_pitches",
        })

        self.assertEqual(result["all_image_urls"], [
            "https://cdn.example.com/p1.jpg",
            "https://cdn.example.com/f1.jpg",
            "https://cdn.example.com/f2.jpg",
        ])
        self.assertIn("IMAGE_INDEX 000 | PRODUCT_IMAGE 001", result["all_image_manifest"])
        self.assertIn("IMAGE_INDEX 001 | VIDEO_FRAME 001", result["all_image_manifest"])
        self.assertIn("PROJECT: LowqualityVideo", result["risk_attention_packet"])
        self.assertIn("RULES_CONTEXT", result["risk_attention_packet"])

    def test_missing_data_panel_records_absent_images_and_frames(self):
        result = self.run_node({
            "video_frame_urls": [],
            "product_image_urls": [],
            "video_data_quality": json.dumps({"video_frames_available": False}),
            "product_data_quality": json.dumps({"product_images_available": False}),
            "comment_data_quality": json.dumps({"comments_available": False}),
        })

        self.assertEqual(result["all_image_urls"], [])
        self.assertIn("NO_IMAGES_AVAILABLE", result["all_image_manifest"])
        self.assertIn("WARNING: product images are missing", result["missing_data_panel"])
        self.assertIn("WARNING: video frames are missing", result["missing_data_panel"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({})

        self.assertEqual(set(result.keys()), {
            "all_image_urls",
            "all_image_manifest",
            "risk_attention_packet",
            "missing_data_panel",
        })


if __name__ == "__main__":
    unittest.main()
