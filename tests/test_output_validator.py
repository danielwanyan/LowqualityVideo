import asyncio
import json
import unittest

from code_nodes import output_validator


class DummyArgs:
    def __init__(self, params):
        self.params = params


class OutputValidatorTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(output_validator.main(DummyArgs(params)))

    def valid_payload(self):
        issue_results = {
            issue: {
                "decision": "no_hit",
                "evidence_cn": "",
                "confidence": "low",
            }
            for issue in output_validator.ALLOWED_ISSUES
        }
        issue_results["only_marketing_sales_pitches"] = {
            "decision": "hit",
            "evidence_cn": "ASR 只有折扣和下单引导，没有商品功能或规格说明。",
            "confidence": "high",
        }
        return {
            "video_id": "7512345678901234567",
            "overall_decision": "problematic",
            "primary_issue_type": "only_marketing_sales_pitches",
            "detected_issue_types": ["only_marketing_sales_pitches"],
            "is_AIGC": "false",
            "issue_results": issue_results,
            "data_quality": {
                "video_frames_available": True,
                "product_images_available": True,
                "asr_available": True,
                "ocr_available": False,
                "missing_or_weak_inputs": [],
            },
            "manual_review_reasons": [],
            "summary_cn": "视频只有营销叫卖。",
            "final_reason_cn": "命中 only_marketing_sales_pitches。",
        }

    def test_accepts_valid_raw_json_and_fills_missing_issue_results(self):
        result = self.run_node({
            "llm_raw_output": json.dumps(self.valid_payload(), ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "ok")
        self.assertEqual(result["overall_decision"], "problematic")
        self.assertEqual(result["primary_issue_type"], "only_marketing_sales_pitches")
        self.assertEqual(result["detected_issue_types"], ["only_marketing_sales_pitches"])
        parsed = json.loads(result["validated_json"])
        self.assertEqual(len(parsed["issue_results"]), 15)
        self.assertEqual(parsed["is_AIGC"], "false")

    def test_fills_missing_issue_results_and_marks_fixed(self):
        payload = self.valid_payload()
        payload["issue_results"] = {
            "only_marketing_sales_pitches": payload["issue_results"]["only_marketing_sales_pitches"],
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        parsed = json.loads(result["validated_json"])
        self.assertEqual(len(parsed["issue_results"]), 15)
        self.assertIn("issue_results normalized to exactly 15 issue keys", result["validation_errors"])

    def test_strips_markdown_fence_and_removes_illegal_labels(self):
        payload = self.valid_payload()
        payload["primary_issue_type"] = "legacy_label"
        payload["detected_issue_types"] = ["only_marketing_sales_pitches", "legacy_label"]
        raw = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"

        result = self.run_node({
            "llm_raw_output": raw,
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertEqual(result["primary_issue_type"], "none")
        self.assertEqual(result["detected_issue_types"], ["only_marketing_sales_pitches"])
        self.assertIn("illegal primary_issue_type", result["validation_errors"])

    def test_illegal_detected_issue_forces_manual_review_even_with_valid_hit(self):
        payload = self.valid_payload()
        payload["detected_issue_types"] = ["only_marketing_sales_pitches", "legacy_label"]

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertEqual(result["detected_issue_types"], ["only_marketing_sales_pitches"])
        self.assertIn("illegal detected_issue_types removed", result["validation_errors"])

    def test_invalid_json_returns_manual_review_not_clean(self):
        result = self.run_node({
            "llm_raw_output": "not json",
            "video_id": "7512345678901234567",
            "is_AIGC": "true",
        })

        self.assertEqual(result["validation_status"], "failed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertEqual(result["primary_issue_type"], "none")
        self.assertEqual(result["detected_issue_types"], [])
        self.assertIn("JSON parse failed", result["validation_errors"])
        self.assertIn("解析失败", result["final_reason_cn"])

    def test_clean_with_hit_issue_result_is_changed_to_manual_review(self):
        payload = self.valid_payload()
        payload["overall_decision"] = "clean"
        payload["primary_issue_type"] = "none"
        payload["detected_issue_types"] = []
        payload["issue_results"]["only_marketing_sales_pitches"] = {
            "decision": "hit",
            "evidence_cn": "ASR 只有促销引导。",
            "confidence": "high",
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertEqual(result["detected_issue_types"], ["only_marketing_sales_pitches"])
        self.assertIn("clean output cannot contain hit issue_results", result["validation_errors"])

    def test_clean_with_uncertain_issue_result_is_changed_to_manual_review(self):
        payload = self.valid_payload()
        payload["overall_decision"] = "clean"
        payload["primary_issue_type"] = "none"
        payload["detected_issue_types"] = []
        payload["issue_results"]["only_marketing_sales_pitches"] = {
            "decision": "uncertain",
            "evidence_cn": "文本疑似只有营销内容。",
            "confidence": "medium",
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertIn("clean output cannot contain uncertain issue_results", result["validation_errors"])

    def test_clean_with_detected_issue_is_changed_to_manual_review(self):
        payload = self.valid_payload()
        payload["overall_decision"] = "clean"
        payload["primary_issue_type"] = "none"
        payload["detected_issue_types"] = ["only_marketing_sales_pitches"]

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertEqual(result["overall_decision"], "manual_review")
        self.assertIn("clean output cannot contain detected_issue_types", result["validation_errors"])

    def test_string_false_data_quality_values_normalize_to_false(self):
        payload = self.valid_payload()
        payload["data_quality"] = {
            "video_frames_available": "false",
            "product_images_available": "true",
            "asr_available": "false",
            "ocr_available": "0",
            "missing_or_weak_inputs": [],
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        data_quality = json.loads(result["data_quality_json"])
        self.assertFalse(data_quality["video_frames_available"])
        self.assertTrue(data_quality["product_images_available"])
        self.assertFalse(data_quality["asr_available"])
        self.assertFalse(data_quality["ocr_available"])

    def test_data_quality_drops_comment_and_review_fields(self):
        payload = self.valid_payload()
        payload["data_quality"]["comments_available"] = True
        payload["data_quality"]["product_review_summary_available"] = True

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        data_quality = json.loads(result["data_quality_json"])
        validated = json.loads(result["validated_json"])
        self.assertNotIn("comments_available", data_quality)
        self.assertNotIn("product_review_summary_available", data_quality)
        self.assertNotIn("comments_available", validated["data_quality"])
        self.assertNotIn("product_review_summary_available", validated["data_quality"])
        self.assertIn("unsupported data_quality fields removed", result["validation_errors"])

    def test_issue_result_hit_is_added_to_detected_issue_types(self):
        payload = self.valid_payload()
        payload["overall_decision"] = "manual_review"
        payload["primary_issue_type"] = "none"
        payload["detected_issue_types"] = []
        payload["issue_results"]["dangerous_behavior"] = {
            "decision": "hit",
            "evidence_cn": "画面展示危险操作。",
            "confidence": "high",
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        self.assertIn("dangerous_behavior", result["detected_issue_types"])
        self.assertIn("hit issue_results added to detected_issue_types", result["validation_errors"])

    def test_invalid_issue_result_enums_are_marked_fixed(self):
        payload = self.valid_payload()
        payload["issue_results"]["only_marketing_sales_pitches"] = {
            "decision": "maybe",
            "evidence_cn": "文本不规范。",
            "confidence": "certain",
        }

        result = self.run_node({
            "llm_raw_output": json.dumps(payload, ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(result["validation_status"], "fixed")
        issue_results = json.loads(result["issue_results_json"])
        self.assertEqual(issue_results["only_marketing_sales_pitches"]["decision"], "no_hit")
        self.assertEqual(issue_results["only_marketing_sales_pitches"]["confidence"], "low")
        self.assertIn("invalid issue_results enum values normalized", result["validation_errors"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({
            "llm_raw_output": json.dumps(self.valid_payload(), ensure_ascii=False),
            "video_id": "7512345678901234567",
            "is_AIGC": "false",
        })

        self.assertEqual(set(result.keys()), {
            "validated_json",
            "validation_status",
            "validation_errors",
            "video_id",
            "overall_decision",
            "primary_issue_type",
            "detected_issue_types",
            "is_AIGC",
            "issue_results_json",
            "data_quality_json",
            "manual_review_reasons_json",
            "summary_cn",
            "final_reason_cn",
        })


if __name__ == "__main__":
    unittest.main()
