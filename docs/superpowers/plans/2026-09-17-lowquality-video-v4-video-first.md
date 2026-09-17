# LowqualityVideo v4 Video-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `LowqualityVideo` from the v3 15-label/manual-review workflow into a video-first binary workflow using only `frame_list`, `ASR`, `OCR`, `images`, and `country` as final LLM evidence.

**Architecture:** Keep one final multimodal LLM. Replace the old active `Rules_Brain -> Context_Builder -> Evidence_Gate -> LLM -> Output_Validator` path with `Video_Content_Builder + Product_Image_Aux_Builder + Boundary_Attention_Builder -> Evidence_Gate -> LLM -> End`.

**Tech Stack:** Python 3 Aicolate Code Nodes, GitHub raw JSON/text rules, Aicolate prompt text files, `python3 -m unittest`.

---

## Implemented Tasks

- [x] Added `product_image_aux_builder.py`, using only `images` and `country`.
- [x] Added `boundary_attention_builder.py`, driven by v4 structured rule JSON.
- [x] Updated `video_content_builder.py` to stop using `url` and `is_AIGC` as evidence.
- [x] Replaced `evidence_gate.py` with a binary, video-first gate.
- [x] Replaced SOP reviewer prompts with video-first binary schema.
- [x] Rewrote `rules/lowquality_video_rules_structured_v1.json` and `rules/lowquality_video_rules_text_v1.txt` to v4.
- [x] Marked old `Rules_Brain`, `Context_Builder`, and `Output_Validator` tests as legacy inactive.
- [x] Added v4 tests for active code nodes, prompts, and rules.
- [x] Added `docs/aicolate-manual-update-2026-09-17.md`.

## Verification

Run:

```bash
python3 -m unittest discover -s /Users/bytedance/LowqualityVideo/tests
python3 -m json.tool /Users/bytedance/LowqualityVideo/rules/lowquality_video_rules_structured_v1.json >/tmp/lowquality_video_rules_check.json
```

Expected:

- Unit tests pass.
- JSON validation exits 0.
- Raw GitHub structured rule URL returns `2026-09-17-v4-video-first-binary-boundary-calibration` after push.

## Aicolate Update Order

1. HTTP rule nodes.
2. `Video_Content_Builder`.
3. `Product_Image_Aux_Builder`.
4. `Boundary_Attention_Builder`.
5. `Evidence_Gate`.
6. `SOP_Multimodal_Risk_Reviewer` prompts.
7. End node direct wiring.

Do not keep `Output_Validator` in the active path.
