import asyncio
import json
import unittest

from code_nodes import product_evidence_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class ProductEvidenceBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(product_evidence_builder.main(DummyArgs(params)))

    def test_parses_json_image_list_and_preserves_signed_urls(self):
        image_one = "https://cdn.example.com/path/a.jpeg?x-signature=abc&expires=123"
        image_two = "https://cdn.example.com/path/b.webp?token=def"
        result = self.run_node({
            "product_id": "1729754192409303107",
            "images": json.dumps([image_one, image_two, image_one]),
            "seller_id_str": "7491234567890123456",
            "country": "GB",
        })

        self.assertEqual(result["product_image_urls"], [image_one, image_two])
        self.assertIn("PRODUCT_IMAGE 001", result["product_image_manifest"])
        self.assertIn("product_local_index=0", result["product_image_manifest"])
        identity = json.loads(result["product_identity_panel"])
        self.assertEqual(identity["product_id"], "1729754192409303107")
        self.assertEqual(identity["seller_id_str"], "7491234567890123456")
        self.assertEqual(identity["country"], "GB")
        quality = json.loads(result["product_data_quality"])
        self.assertTrue(quality["product_images_available"])
        self.assertEqual(quality["product_image_count"], 2)

    def test_extracts_urls_from_nested_json_and_text_markers(self):
        images = {
            "main": "[Image #1] https://cdn.example.com/main.jpg",
            "variants": [
                {"url": "https://cdn.example.com/variant.png"},
                "not a url",
            ],
        }
        result = self.run_node({
            "product_id": "p1",
            "images": json.dumps(images),
            "seller_id_str": "",
            "country": "DE",
        })

        self.assertEqual(result["product_image_urls"], [
            "https://cdn.example.com/main.jpg",
            "https://cdn.example.com/variant.png",
        ])
        self.assertIn("PRODUCT_IMAGE_COUNT: 2", result["product_image_manifest"])

    def test_empty_images_reports_missing_reference_warning(self):
        result = self.run_node({
            "product_id": "",
            "images": "",
            "seller_id_str": "",
            "country": "",
        })

        self.assertEqual(result["product_image_urls"], [])
        quality = json.loads(result["product_data_quality"])
        self.assertFalse(quality["product_images_available"])
        self.assertIn("images is empty or invalid", quality["warnings"][0])
        self.assertIn("product_id is empty", quality["warnings"])

    def test_output_keys_match_aicolate_output_panel(self):
        result = self.run_node({
            "product_id": "p1",
            "images": "[]",
            "seller_id_str": "s1",
            "country": "GB",
        })

        self.assertEqual(set(result.keys()), {
            "product_image_urls",
            "product_image_manifest",
            "product_identity_panel",
            "product_data_quality",
        })


if __name__ == "__main__":
    unittest.main()
