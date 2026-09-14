# LowqualityVideo Aicolate Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `LowqualityVideo` Aicolate workflow with the confirmed 15-label SOP scope, existing `video-product-lowquality` input shape, and the new `is_AIGC` field.

**Architecture:** Use a dedicated GitHub rule source, input builder code nodes, Rules Brain, Context Builder, Evidence Gate, one multimodal reviewer, and Output Validator. The user will update the Aicolate canvas manually one node at a time.

**Tech Stack:** Aicolate Start fields, HTTP Request nodes, Python Code Nodes using `async def main(args: Args) -> Output`, GitHub raw rule files, one multimodal LLM node, JSON validator.

---

## File Structure

- Create `rules/lowquality_video_rules_structured_v1.json`: structured rules for the 15 labels.
- Create `rules/lowquality_video_rules_text_v1.txt`: human-readable compressed rule text for HTTP fallback and prompt context.
- Create `code_nodes/video_content_builder.py`: parse video fields, frame list, and `is_AIGC`.
- Create `code_nodes/product_evidence_builder.py`: parse product reference images and product identity.
- Create `code_nodes/comment_signal_builder.py`: extract supporting comment signals without creating unsupported labels.
- Create `code_nodes/rules_brain.py`: select relevant rule families and apply `is_AIGC` attention only to `unrealistic_or_continuity_error`.
- Create `code_nodes/context_builder.py`: assemble image order and prompt evidence packet.
- Create `code_nodes/evidence_gate.py`: block claims when required evidence is absent.
- Create `code_nodes/output_validator.py`: enforce legal JSON schema and enum values.
- Create `prompts/sop_multimodal_risk_reviewer_system_prompt.txt`: pure text system prompt.
- Create `prompts/sop_multimodal_risk_reviewer_user_prompt.txt`: user prompt with `{{}}` variable references.
- Create `tests/test_code_nodes.py`: local unit tests for parsing, rule attention, evidence gates, and output validation.

## Task 1: Start Node

- [ ] Create a new Aicolate workflow named `LowqualityVideo`.
- [ ] Add 13 Start fields as String: `video_id`, `OCR`, `ASR`, `country`, `author_id`, `url`, `product_id`, `images`, `seller_id_str`, `comments`, `product_review_summary`, `frame_list`, `is_AIGC`.
- [ ] Run one Start preview and confirm long IDs remain strings.

## Task 2: GitHub Rule HTTP Nodes

- [ ] Commit and push `rules/lowquality_video_rules_structured_v1.json` and `rules/lowquality_video_rules_text_v1.txt`.
- [ ] Verify both raw GitHub URLs return the expected files.
- [ ] Add Aicolate HTTP node `lowquality_video_rules_json_fetch`.
- [ ] Add Aicolate HTTP node `lowquality_video_rules_text_fetch`.
- [ ] Confirm both HTTP nodes output non-empty `body` fields.

## Task 3: Builder Nodes

- [ ] Add `Video_Content_Builder` with full paste-ready code and output fields from the design spec.
- [ ] Add `Product_Evidence_Builder` with full paste-ready code and output fields from the design spec.
- [ ] Add `Comment_Signal_Builder` with full paste-ready code and output fields from the design spec.
- [ ] Run each node with one sample and confirm output panels match returned keys.

## Task 4: Rules Brain, Context Builder, Evidence Gate

- [ ] Add `Rules_Brain` and wire HTTP `body` outputs plus builder outputs.
- [ ] Add `Context_Builder` and wire all builder and Rules Brain outputs.
- [ ] Add `Evidence_Gate` and wire Context Builder outputs plus data quality fields.
- [ ] Run a sample through the pre-LLM path and confirm `gated_risk_attention_packet` is non-empty.

## Task 5: LLM Reviewer and Output Validator

- [ ] Add `SOP_Multimodal_Risk_Reviewer` with pure text system prompt.
- [ ] Add user prompt with `{{}}` variable references only.
- [ ] Add `Output_Validator` with full paste-ready code.
- [ ] Wire final End fields from Output Validator.
- [ ] Run smoke tests covering one normal sample, one missing-frame sample, and one AIGC sample.

## Verification

- [ ] Run local unit tests with `python3 -m unittest`.
- [ ] Validate structured rules with `python3 -m json.tool`.
- [ ] Verify GitHub raw URLs after push.
- [ ] Confirm Aicolate node previews expose exact output field names.
