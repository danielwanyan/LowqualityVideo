import asyncio
import json
import unittest

from code_nodes import comment_signal_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class CommentSignalBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(comment_signal_builder.main(DummyArgs(params)))

    def test_extracts_relevant_comment_clusters_without_final_hits(self):
        comments = "\n".join([
            "[0] ccr_list: ContentIssue--CopiedContent | text: This is stolen from Douyin, original creator watermark is visible",
            "[1] ccr_list: TransactionIssue--OffPlatform | text: PayPal me and contact my WhatsApp to buy",
            "[2] ccr_list: ContentIssue--Vulgar | text: too sexy and vulgar for product promotion",
        ])
        result = self.run_node({
            "comments": comments,
            "product_review_summary": "Reviews are mixed but no product defect pattern.",
            "product_id": "1729754192409303107",
        })

        clusters = json.loads(result["comment_issue_clusters"])
        self.assertIn("pirated_or_reposted_claim", clusters["cluster_types"])
        self.assertIn("out_of_app_transaction_claim", clusters["cluster_types"])
        self.assertIn("pornography_or_vulgar_claim", clusters["cluster_types"])
        self.assertIn("Comments are supporting signals only", result["comment_risk_summary"])
        quality = json.loads(result["comment_data_quality"])
        self.assertEqual(quality["parsed_comment_count"], 3)

    def test_plain_multiline_comments_are_still_scanned(self):
        comments = "\n".join([
            "This ad is fake AI and the product never appears.",
            "Only says buy now discount ends today.",
        ])
        result = self.run_node({
            "comments": comments,
            "product_review_summary": "",
            "product_id": "p1",
        })

        clusters = json.loads(result["comment_issue_clusters"])
        self.assertIn("unrealistic_or_aigc_claim", clusters["cluster_types"])
        self.assertIn("no_physical_product_display_claim", clusters["cluster_types"])
        self.assertIn("only_marketing_claim", clusters["cluster_types"])

    def test_empty_comments_reports_no_comment_evidence(self):
        result = self.run_node({
            "comments": "",
            "product_review_summary": "",
            "product_id": "",
        })

        self.assertEqual(result["representative_comment_quotes"], "")
        clusters = json.loads(result["comment_issue_clusters"])
        self.assertEqual(clusters["cluster_types"], [])
        quality = json.loads(result["comment_data_quality"])
        self.assertFalse(quality["comments_available"])
        self.assertIn("comments is empty", quality["warnings"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({
            "comments": "",
            "product_review_summary": "Buyer says the effect is misleading and dangerous.",
            "product_id": "p1",
        })

        self.assertEqual(set(result.keys()), {
            "comment_risk_summary",
            "comment_issue_clusters",
            "representative_comment_quotes",
            "comment_data_quality",
        })


if __name__ == "__main__":
    unittest.main()
