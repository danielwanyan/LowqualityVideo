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
            "all_image_urls": ["https://cdn.example.com/p.jpg", "https://cdn.example.com/f.jpg"],
            "all_image_manifest": "IMAGE_INDEX 000 | PRODUCT_IMAGE 001\nIMAGE_INDEX 001 | VIDEO_FRAME 001",
            "product_image_urls": ["https://cdn.example.com/p.jpg"],
            "video_frame_urls": ["https://cdn.example.com/f.jpg"],
            "video_data_quality": json.dumps({"video_frames_available": True, "asr_available": True, "ocr_available": False}),
            "product_data_quality": json.dumps({"product_images_available": True}),
            "comment_data_quality": json.dumps({"comments_available": True, "product_review_summary_available": False}),
            "comment_issue_clusters": json.dumps({"cluster_types": []}),
            "risk_attention_packet": "PROJECT: LowqualityVideo",
            "missing_data_panel": "none",
        })

        status = json.loads(result["evidence_status_json"])
        self.assertIn("inconsistent_product_promotion", status["allowed_issue_types"])
        self.assertIn("potential_pirated", status["allowed_issue_types"])
        self.assertEqual(status["recommended_decision_floor"], "no_floor")
        self.assertEqual(result["gated_all_image_urls"], [
            "https://cdn.example.com/p.jpg",
            "https://cdn.example.com/f.jpg",
        ])

    def test_blocks_visual_claims_when_frames_missing(self):
        result = self.run_node({
            "all_image_urls": ["https://cdn.example.com/p.jpg"],
            "product_image_urls": ["https://cdn.example.com/p.jpg"],
            "video_frame_urls": [],
            "video_data_quality": json.dumps({"video_frames_available": False, "asr_available": True, "ocr_available": True}),
            "product_data_quality": json.dumps({"product_images_available": True}),
            "comment_data_quality": json.dumps({"comments_available": False}),
            "comment_issue_clusters": json.dumps({"cluster_types": []}),
        })

        status = json.loads(result["evidence_status_json"])
        self.assertNotIn("still_frame", status["allowed_issue_types"])
        self.assertNotIn("pirated_content", status["allowed_issue_types"])
        self.assertNotIn("unrealistic_or_continuity_error", status["allowed_issue_types"])
        self.assertIn("Do not make video-frame visual claims", result["forbidden_claims"])

    def test_comment_only_piracy_signal_sets_manual_review_floor(self):
        result = self.run_node({
            "product_image_urls": [],
            "video_frame_urls": [],
            "video_data_quality": json.dumps({"video_frames_available": False, "asr_available": False, "ocr_available": False}),
            "product_data_quality": json.dumps({"product_images_available": False}),
            "comment_data_quality": json.dumps({"comments_available": True, "meaningful_comment_count": 2}),
            "comment_issue_clusters": json.dumps({"cluster_types": ["pirated_or_reposted_claim"]}),
        })

        status = json.loads(result["evidence_status_json"])
        self.assertTrue(status["comment_only_piracy_signal"])
        self.assertEqual(status["recommended_decision_floor"], "manual_review_for_comment_only_piracy_signal")
        self.assertIn("Comments alone cannot support pirated_content", result["forbidden_claims"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({})

        self.assertEqual(set(result.keys()), {
            "gated_all_image_urls",
            "gated_all_image_manifest",
            "evidence_gate_panel",
            "gated_risk_attention_packet",
            "evidence_status_json",
            "allowed_issue_types",
            "forbidden_claims",
            "recommended_decision_floor",
        })


if __name__ == "__main__":
    unittest.main()
