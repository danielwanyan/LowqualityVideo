# Aicolate Manual Update Guide - LowqualityVideo v4

## Step 0: Evidence Boundary

Final LLM judgment evidence is limited to:

- `frame_list`
- `ASR`
- `OCR`
- `images`
- `country`

Keep these fields for human display or tracing only. Do not wire them into the final LLM prompt:

- `url`
- `product_id`
- `seller_id_str`
- `comments`
- `product_review_summary`
- `is_AIGC`

## Step 1: HTTP Rule Nodes

Use these raw URLs:

- `https://raw.githubusercontent.com/danielwanyan/LowqualityVideo/main/rules/lowquality_video_rules_structured_v1.json`
- `https://raw.githubusercontent.com/danielwanyan/LowqualityVideo/main/rules/lowquality_video_rules_text_v1.txt`

After push, rerun both HTTP nodes and confirm the structured rule version is:

```text
2026-09-17-v4-video-first-binary-boundary-calibration
```

## Step 2: Video_Content_Builder

Input Variables:

- `frame_list = {{frame_list}}`
- `ASR = {{ASR}}`
- `OCR = {{OCR}}`
- `video_id = {{video_id}}`

Do not wire `url` or `is_AIGC`.

Output panel:

- `video_frame_urls`
- `video_frame_manifest`
- `video_text_panel`
- `video_signal_flags_json`
- `video_signal_panel`
- `video_data_quality_json`
- `video_data_quality`

Paste full code from:

```text
/Users/bytedance/LowqualityVideo/code_nodes/video_content_builder.py
```

Stop here and run one sample before continuing.

## Step 3: Product_Image_Aux_Builder

Input Variables:

- `images = {{images}}`
- `country = {{country}}`

Do not wire `product_id`, `seller_id_str`, `comments`, or `product_review_summary`.

Output panel:

- `product_image_urls`
- `product_image_manifest`
- `product_aux_panel`
- `product_aux_data_quality_json`

Paste full code from:

```text
/Users/bytedance/LowqualityVideo/code_nodes/product_image_aux_builder.py
```

Stop here and run one sample before continuing.

## Step 4: Boundary_Attention_Builder

Input Variables:

- `video_text_panel = {{video_text_panel}}`
- `video_data_quality_json = {{video_data_quality_json}}`
- `product_aux_panel = {{product_aux_panel}}`
- `product_aux_data_quality_json = {{product_aux_data_quality_json}}`
- `rules_json_body = {{lowquality_video_rules_json_fetch.body}}`
- `rules_text_body = {{lowquality_video_rules_text_fetch.body}}`

Output panel:

- `boundary_attention_packet`
- `active_boundary_groups`
- `must_not_infer`
- `positive_hit_tests`
- `allowed_issue_types`

Paste full code from:

```text
/Users/bytedance/LowqualityVideo/code_nodes/boundary_attention_builder.py
```

Stop here and run one sample before continuing.

## Step 5: Evidence_Gate

## Step 5: Issue_Boundary_Gate_Builder

Input Variables:

- `video_text_panel = {{video_text_panel}}`
- `video_data_quality_json = {{video_data_quality_json}}`
- `product_aux_panel = {{product_aux_panel}}`
- `product_aux_data_quality_json = {{product_aux_data_quality_json}}`

Output panel:

- `issue_boundary_gates_json`
- `issue_boundary_gate_panel`

Paste full code from:

```text
/Users/bytedance/LowqualityVideo/code_nodes/issue_boundary_gate_builder.py
```

Stop here and run one sample before continuing.

## Step 6: Evidence_Gate

Input Variables:

- `video_frame_urls = {{video_frame_urls}}`
- `video_frame_manifest = {{video_frame_manifest}}`
- `video_data_quality_json = {{video_data_quality_json}}`
- `product_image_urls = {{product_image_urls}}`
- `product_image_manifest = {{product_image_manifest}}`
- `product_aux_data_quality_json = {{product_aux_data_quality_json}}`
- `boundary_attention_packet = {{boundary_attention_packet}}`
- `issue_boundary_gate_panel = {{issue_boundary_gate_panel}}`
- `allowed_issue_types = {{allowed_issue_types}}`

Output panel:

- `gated_all_image_urls`
- `gated_all_image_manifest`
- `evidence_gate_panel`
- `forbidden_claims`
- `allowed_issue_types`
- `final_reviewer_context`

Paste full code from:

```text
/Users/bytedance/LowqualityVideo/code_nodes/evidence_gate.py
```

Stop here and run one sample before continuing.

## Step 7: SOP_Multimodal_Risk_Reviewer

System Prompt:

```text
/Users/bytedance/LowqualityVideo/prompts/sop_multimodal_risk_reviewer_system_prompt.txt
```

User Prompt:

```text
/Users/bytedance/LowqualityVideo/prompts/sop_multimodal_risk_reviewer_user_prompt.txt
```

Input Variables:

- `gated_all_image_urls = {{gated_all_image_urls}}`
- `gated_all_image_manifest = {{gated_all_image_manifest}}`
- `final_reviewer_context = {{final_reviewer_context}}`
- `evidence_gate_panel = {{evidence_gate_panel}}`
- `allowed_issue_types = {{allowed_issue_types}}`
- `forbidden_claims = {{forbidden_claims}}`
- `video_id = {{video_id}}`
- `ASR = {{ASR}}`
- `OCR = {{OCR}}`
- `country = {{country}}`

Do not wire `url`, `product_id`, `seller_id_str`, `comments`, `product_review_summary`, or `is_AIGC`.

## Step 8: End Node

Connect End directly to the single output field from `SOP_Multimodal_Risk_Reviewer`.

Remove these nodes from the active path:

- `Rules_Brain`
- `Context_Builder`
- `Output_Validator`

## Step 9: Smoke Test

Run three samples:

- a known clean color-only mismatch false positive;
- a known problematic MFE sample;
- a known frame-missing sample if available.

Expected:

- no `manual_review`;
- no `tagsProduct`;
- `ratings` is `["video"]` for issues and `["ok"]` for clean;
- display-only fields are not referenced in `final_reason_cn`.
