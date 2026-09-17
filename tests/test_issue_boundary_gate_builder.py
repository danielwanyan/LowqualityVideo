import asyncio
import json
import unittest

from code_nodes import issue_boundary_gate_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class IssueBoundaryGateBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(issue_boundary_gate_builder.main(DummyArgs(params)))

    def test_outputs_structured_gates_for_high_fp_issue_types(self):
        result = self.run_node({
            "video_text_panel": json.dumps({
                "asr_text": "This razor gives laser-like smooth skin. Buy now.",
                "ocr_text": "50% off",
                "signals": {
                    "has_hard_sell_terms": True,
                    "has_substantive_product_terms": False,
                    "has_misleading_terms": True,
                    "has_pirated_terms": False,
                },
            }, ensure_ascii=False),
            "video_data_quality_json": json.dumps({
                "video_frames_available": True,
                "asr_available": True,
                "ocr_available": True,
            }, ensure_ascii=False),
            "product_aux_panel": "COUNTRY: ES\nPRODUCT_IMAGE_COUNT: 2",
            "product_aux_data_quality_json": json.dumps({
                "product_images_available": True,
                "country_available": True,
            }, ensure_ascii=False),
        })

        gates = json.loads(result["issue_boundary_gates_json"])
        self.assertEqual(gates["mfe"]["required_claim_source"], "frame_list_or_ASR_or_OCR")
        self.assertIn("product_image_only", gates["mfe"]["blocked_claim_sources"])
        self.assertEqual(gates["ipp"]["allowed_difference_types"], [
            "core_product_type",
            "core_function",
            "package_count_or_quantity",
            "visible_size_or_dimension",
        ])
        self.assertIn("color_only", gates["ipp"]["blocked_difference_types"])
        self.assertEqual(gates["piracy"]["minimum_strong_signal_count"], 2)
        self.assertEqual(gates["still_frame"]["strictness"], "very_high")
        self.assertEqual(gates["continuity"]["priority"], "low")
        self.assertIn("MFE_CLAIM_GATE", result["issue_boundary_gate_panel"])
        self.assertIn("IPP_DIFFERENCE_GATE", result["issue_boundary_gate_panel"])
        self.assertIn("PIRACY_SIGNAL_GATE", result["issue_boundary_gate_panel"])

    def test_does_not_include_display_only_source_values(self):
        result = self.run_node({
            "video_text_panel": "{}",
            "video_data_quality_json": "{}",
            "product_aux_panel": "COUNTRY: FR",
            "product_aux_data_quality_json": "{}",
            "comments": "must-not-appear",
            "product_review_summary": "must-not-appear",
            "product_id": "must-not-appear",
            "seller_id_str": "must-not-appear",
            "url": "must-not-appear",
        })

        joined = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("must-not-appear", joined)
        self.assertNotIn("product_review_summary", joined)
        self.assertNotIn("comments", joined)


if __name__ == "__main__":
    unittest.main()
