import asyncio
import json
import unittest

from code_nodes import evidence_gate


class DummyArgs:
    def __init__(self, params):
        self.params = params


class EvidenceGateTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(evidence_gate.main(DummyArgs(params)))

    def test_allows_visual_and_product_claims_when_evidence_exists(self):
        result = self.run_node({
            "product_image_urls": ["https://cdn.example.com/p.jpg"],
            "video_frame_urls": ["https://cdn.example.com/f.jpg"],
            "video_frame_manifest": "VIDEO_FRAME 001 | f.jpg",
            "product_image_manifest": "PRODUCT_IMAGE 001 | p.jpg",
            "video_data_quality_json": json.dumps({"video_frames_available": True, "asr_available": True, "ocr_available": False}),
            "product_aux_data_quality_json": json.dumps({"product_images_available": True, "country_available": True}),
            "boundary_attention_packet": "PROJECT: LowqualityVideo",
            "allowed_issue_types": "video_product_mismatch, none",
        })

        self.assertIn("Allowed final decisions: problematic, clean", result["final_reviewer_context"])
        self.assertIn("PROJECT: LowqualityVideo", result["final_reviewer_context"])
        self.assertEqual(result["gated_all_image_urls"], [
            "https://cdn.example.com/p.jpg",
            "https://cdn.example.com/f.jpg",
        ])

    def test_blocks_visual_claims_when_frames_missing(self):
        result = self.run_node({
            "product_image_urls": ["https://cdn.example.com/p.jpg"],
            "video_frame_urls": [],
            "video_data_quality_json": json.dumps({"video_frames_available": False, "asr_available": True, "ocr_available": True}),
            "product_aux_data_quality_json": json.dumps({"product_images_available": True, "country_available": True}),
        })

        self.assertIn("不要描述视频画面证据", result["forbidden_claims"])
        self.assertIn("视频不可见", result["evidence_gate_panel"])

    def test_all_core_evidence_missing_defaults_to_clean_guidance(self):
        result = self.run_node({
            "product_image_urls": [],
            "video_frame_urls": [],
            "video_data_quality_json": json.dumps({"video_frames_available": False, "asr_available": False, "ocr_available": False}),
            "product_aux_data_quality_json": json.dumps({"product_images_available": False, "country_available": False}),
        })

        self.assertIn("choose clean", result["final_reviewer_context"])
        self.assertNotIn("manual_review", json.dumps(result, ensure_ascii=False))

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({})

        self.assertEqual(set(result.keys()), {
            "gated_all_image_urls",
            "gated_all_image_manifest",
            "evidence_gate_panel",
            "forbidden_claims",
            "allowed_issue_types",
            "final_reviewer_context",
        })


if __name__ == "__main__":
    unittest.main()
