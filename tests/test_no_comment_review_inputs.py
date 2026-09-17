import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NoCommentReviewInputsTest(unittest.TestCase):
    def test_runtime_nodes_do_not_read_comment_or_review_inputs(self):
        runtime_files = [
            ROOT / "code_nodes" / "video_content_builder.py",
            ROOT / "code_nodes" / "product_image_aux_builder.py",
            ROOT / "code_nodes" / "boundary_attention_builder.py",
            ROOT / "code_nodes" / "evidence_gate.py",
            ROOT / "prompts" / "sop_multimodal_risk_reviewer_system_prompt.txt",
            ROOT / "prompts" / "sop_multimodal_risk_reviewer_user_prompt.txt",
            ROOT / "rules" / "lowquality_video_rules_structured_v1.json",
            ROOT / "rules" / "lowquality_video_rules_text_v1.txt",
        ]

        forbidden = [
            "params.get(\"comments\")",
            "params.get(\"product_review_summary\")",
            "{{comments}}",
            "{{product_review_summary}}",
            "comment_risk_summary",
            "comment_issue_clusters",
            "representative_comment_quotes",
            "comment_data_quality",
            "comments_available",
            "product_review_summary_available",
        ]
        for path in runtime_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{token} found in {path}")

    def test_no_comment_signal_builder_file_exists(self):
        self.assertFalse((ROOT / "code_nodes" / "comment_signal_builder.py").exists())
        self.assertFalse((ROOT / "tests" / "test_comment_signal_builder.py").exists())


if __name__ == "__main__":
    unittest.main()
