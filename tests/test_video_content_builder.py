import asyncio
import json
import unittest

from code_nodes import video_content_builder


class DummyArgs:
    def __init__(self, params):
        self.params = params


class VideoContentBuilderTest(unittest.TestCase):
    def run_node(self, params):
        return asyncio.run(video_content_builder.main(DummyArgs(params)))

    def test_parses_newline_frame_list_and_normalizes_is_aigc_true(self):
        result = self.run_node({
            "video_id": "7512345678901234567",
            "url": "https://example.com/video",
            "frame_list": "https://cdn.example.com/f1.jpg\nhttps://cdn.example.com/f2.jpg",
            "ASR": "Add to cart now, buy one get one free.",
            "OCR": "PayPal me for faster delivery",
            "is_AIGC": "yes",
        })

        self.assertEqual(result["video_frame_urls"], [
            "https://cdn.example.com/f1.jpg",
            "https://cdn.example.com/f2.jpg",
        ])
        data_quality = json.loads(result["video_data_quality"])
        self.assertTrue(data_quality["video_frames_available"])
        self.assertEqual(data_quality["is_AIGC"], "true")
        signal_panel = json.loads(result["video_signal_panel"])
        self.assertTrue(signal_panel["signals"]["has_hard_sell_terms"])
        self.assertTrue(signal_panel["signals"]["has_external_transaction_terms"])

    def test_parses_json_frame_list_and_normalizes_unknown_is_aigc(self):
        result = self.run_node({
            "frame_list": "[\"https://cdn.example.com/a.webp\", \"https://cdn.example.com/b.png\"]",
            "ASR": "",
            "OCR": "",
            "is_AIGC": "not sure",
        })

        self.assertEqual(result["video_frame_urls"], [
            "https://cdn.example.com/a.webp",
            "https://cdn.example.com/b.png",
        ])
        data_quality = json.loads(result["video_data_quality"])
        self.assertEqual(data_quality["is_AIGC"], "unknown")
        self.assertIn("ASR and OCR are both empty", data_quality["warnings"])

    def test_invalid_empty_frame_list_blocks_visual_availability(self):
        result = self.run_node({
            "frame_list": "",
            "ASR": "",
            "OCR": "中文贴纸",
            "is_AIGC": "false",
        })

        self.assertEqual(result["video_frame_urls"], [])
        data_quality = json.loads(result["video_data_quality"])
        self.assertFalse(data_quality["video_frames_available"])
        self.assertEqual(data_quality["is_AIGC"], "false")
        self.assertIn("frame_list is empty", data_quality["warnings"][0])


if __name__ == "__main__":
    unittest.main()
