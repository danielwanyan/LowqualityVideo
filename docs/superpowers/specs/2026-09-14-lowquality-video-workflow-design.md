# LowqualityVideo Aicolate Workflow Design

Date: 2026-09-14
Status: user-approved design draft

## Goal

Build a new Aicolate workflow project named `LowqualityVideo`.

The workflow reuses the verified input shape and orchestration pattern from the existing `video-product-lowquality` project, but it uses a new rule set, new GitHub rule source, and a new output label taxonomy. It does not attempt to cover the full SOP document. The recognition scope is limited to the issue list confirmed by the user.

## Sources

- SOP doc: `https://bytedance.sg.larkoffice.com/docx/W1tpdXKkmox4Bixe8FslXiYVgqf`
- Existing workflow reference: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/video-product-lowquality/Video-Product-Lowquality-Workflow.md`
- Existing output schema reference: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/video-product-lowquality/Video-Product-Lowquality-Output-Schema.md`
- Existing evidence gate reference: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/video-product-lowquality/code_nodes/evidence_gate.py`
- New GitHub rule repository: `https://github.com/danielwanyan/LowqualityVideo`

## Explicit Non-Goals

- Do not cover the complete SOP.
- Do not add external Pearl fields such as Similar Video tab, creator profile, penalty record, account ownership, or creator history.
- Do not let `is_AIGC` create a direct violation by itself.
- Do not inherit old project labels or product-quality-specific rules that are outside the confirmed label list.

## Start Inputs

The workflow uses the following video and product evidence fields and adds one AIGC attribute field:

```text
video_id
OCR
ASR
country
url
product_id
images
seller_id_str
frame_list
is_AIGC
```

Field semantics:

- `frame_list`: up to 8 video frame URLs sampled uniformly across the full video duration, in chronological order.
- `ASR`: speech transcript text. It can be empty.
- `OCR`: visual text extracted from video frames. It can be empty.
- `images`: product reference image URLs, normally encoded as a JSON list.
- `is_AIGC`: an attribute field indicating whether the video is marked as AIGC generated.

`is_AIGC` behavior:

- It is returned as an attribute in the output.
- It only increases attention for `unrealistic_or_continuity_error`.
- It does not increase attention for `misleading_functionality_and_effect`, `no_physical_product_display`, `still_frame`, or any other issue type.
- It never creates a hit without concrete frame, ASR, OCR, or product image evidence.

## In-Scope Issue Types

The final workflow may only output the following issue types:

```text
potential_pirated
irrelevant_promotion
pirated_content
inconsistent_product_promotion
non_native
still_frame
out_of_app_transactions
misleading_functionality_and_effect
dangerous_behavior
disgusting_and_terrifying
description_not_detailed
only_marketing_sales_pitches
pornography_perception
no_physical_product_display
unrealistic_or_continuity_error
none
```

The first 15 values are problem labels. `none` is only used when no issue is detected.

## Workflow Topology

```text
Start
  ├─ HTTP: lowquality_video_rules_json_fetch
  ├─ HTTP: lowquality_video_rules_text_fetch
  ├─ Code: Video_Content_Builder
  ├─ Code: Product_Evidence_Builder
  └─ Code: Rules_Brain
       ↓
Code: Context_Builder
       ↓
Code: Evidence_Gate
       ↓
LLM: SOP_Multimodal_Risk_Reviewer
       ↓
Code: Output_Validator
       ↓
End
```

This keeps the verified pattern from the previous workflow:

- Builder nodes normalize inputs and create compact evidence panels.
- Rules Brain retrieves only the relevant rule families.
- Context Builder assembles multimodal inputs in a stable order.
- Evidence Gate prevents hallucinated claims when evidence is missing.
- One multimodal LLM makes the final semantic judgment.
- Output Validator enforces strict JSON shape and legal enum values.

## GitHub Rule Sources

The workflow will fetch its own rule files from the new repository:

```text
https://raw.githubusercontent.com/danielwanyan/LowqualityVideo/main/rules/lowquality_video_rules_structured_v1.json
https://raw.githubusercontent.com/danielwanyan/LowqualityVideo/main/rules/lowquality_video_rules_text_v1.txt
```

These files are the source of truth for Aicolate HTTP nodes. Rule updates should be pushed to GitHub and verified by reading the raw URLs before the user updates Aicolate nodes.

## Node Responsibilities

### Video_Content_Builder

Inputs:

```text
frame_list
ASR
OCR
url
video_id
is_AIGC
```

Outputs:

```text
video_frame_urls
video_frame_manifest
video_text_panel
aigc_attribute_panel
video_signal_panel
video_data_quality
```

Responsibilities:

- Parse `frame_list` into ordered frame URLs.
- Build a stable frame manifest using frame numbers.
- Summarize ASR/OCR evidence relevant to the 15 labels.
- Preserve `is_AIGC` as an input attribute.
- Surface candidate signals such as hard-sell language, off-platform payment language, non-native language cues, static-frame cues, and pirated/spliced visual cues.
- Avoid final judgments.

### Product_Evidence_Builder

Inputs:

```text
product_id
images
seller_id_str
country
```

Outputs:

```text
product_image_urls
product_image_manifest
product_identity_panel
product_data_quality
```

Responsibilities:

- Parse product image URLs.
- Preserve `product_id`, `seller_id_str`, and `country`.
- Provide product reference images for `inconsistent_product_promotion`, `no_physical_product_display`, and `misleading_functionality_and_effect`.
- Mark product image missing or invalid states.
- Avoid final judgments.

### Rules_Brain

Inputs:

```text
rules_json_body
rules_text_body
video_signal_panel
product_identity_panel
aigc_attribute_panel
```

Outputs:

```text
rules_context
matched_rule_families
rule_attention_debug
```

Responsibilities:

- Select rule families for only the 15 in-scope issue types.
- Include missing-evidence constraints from the structured rule file.
- Increase attention for `unrealistic_or_continuity_error` when `is_AIGC` is true or when frame evidence suggests morphing, clipping, product geometry drift, object materialization, garbled text, or other physical-reality errors.
- Do not increase attention for unrelated labels just because `is_AIGC` is true.

### Context_Builder

Inputs:

```text
video_frame_urls
video_frame_manifest
video_text_panel
aigc_attribute_panel
video_signal_panel
product_image_urls
product_image_manifest
product_identity_panel
rules_context
matched_rule_families
```

Outputs:

```text
all_image_urls
all_image_manifest
risk_attention_packet
missing_data_panel
```

Responsibilities:

- Put product images before video frames in `all_image_urls`.
- Explain the image order in `all_image_manifest`.
- Preserve the frame sampling contract.
- Separate video evidence, product reference evidence, AIGC attribute, and rule context.

### Evidence_Gate

Inputs:

```text
video_frame_urls
product_image_urls
video_data_quality
product_data_quality
risk_attention_packet
missing_data_panel
```

Outputs:

```text
gated_all_image_urls
gated_all_image_manifest
evidence_gate_panel
gated_risk_attention_packet
evidence_status_json
allowed_issue_types
forbidden_claims
recommended_decision_floor
```

Responsibilities:

- Block visual claims when video frames are missing.
- Block product comparison claims when product images are missing.
- Block ASR/OCR-only labels when text is missing.
- Recommend `manual_review` when there are risk signals but necessary evidence is incomplete.
- Explicitly tell the LLM which claims are forbidden.

### SOP_Multimodal_Risk_Reviewer

Responsibilities:

- Review all images and text evidence together.
- Output raw JSON only.
- Use only the in-scope label enum.
- Mark all applicable labels in `detected_issue_types`.
- Select one `primary_issue_type`.
- Explain all decisions in Chinese.
- For pirated and potential pirated, require strong evidence and avoid over-labeling ordinary montage or style shifts.

### Output_Validator

Responsibilities:

- Strip Markdown code fences if the model returns them.
- Parse the JSON object.
- Fill missing required fields with safe defaults.
- Reject illegal issue labels by moving the result to `manual_review` and adding a schema warning.
- Never silently convert a malformed risky output to `clean`.

## Evidence Thresholds

### Pirated content and potential pirated

The workflow must use a high evidence threshold to avoid false positives.

Direct `pirated_content` requires strong evidence such as:

- Visible third-party creator watermark, username, platform mark, or repost signal in the video frame.
- Clear ASR/OCR evidence that the clip was copied, reposted, or taken from another creator.
- A duet-like layout where the creator contributes no meaningful new product promotion and only carries another creator's product promotion.

Direct `potential_pirated` can be used for:

- Frequent clip switching with different people, hands, scenery, framing, or production styles that strongly suggest multi-source splicing.
- Sandwich or AB-style composition visible from video frames.
- Inconsistent scene tracks that suggest repurposed domestic or other-creator footage.

Do not hit either label for:

- Ordinary montage or normal editing.
- Product demo clips from a likely brand account or brand owner when authorization cannot be ruled out.
- Public-resource footage such as movies or TV content unless it is used as another in-scope issue.
- Weak visual style shifts without concrete source or splicing evidence.

If suspicious but not conclusive, output `manual_review` and explain the evidence gap in `manual_review_reasons`, but do not label it as a hit.

### Irrelevant promotion

Hit when video content is unrelated to e-commerce product promotion and is mainly entertainment or storytelling, even if the bound product appears briefly, flashes by, or cannot be clearly identified.

### Inconsistent product promotion

Hit when video ASR/OCR or frames promote an EC product but the displayed product differs from the bound product reference images. Product images are required for a strong hit.

Exemptions:

- Blind boxes, accessories, jade, and collectible cards can be exempted when displayed and bound products are in the same L3 category.
- Apparel tops and bottoms can be exempted when the displayed product is a SKU variant of the bound product with only pattern or color differences.

### Non-native

Hit when the video shows Chinese or incomprehensible Chinglish style in an international market, such as long Chinese spoken expression, Chinese text/stickers/background, or English that is difficult to understand because of severe grammar or expression issues.

This is separate from the SOP's broader `Other languages` personalized problem. The new workflow only covers `non_native` from the confirmed list.

### Still frame

Hit when the video has no verbal or written product explanation and the product display is made of static images, live photos, screenshots, or cutout-style pasted product images without real video footage.

### Out-of-app transactions

Hit when evidence shows both:

- a payment or transaction route outside the platform, such as PayPal, Venmo, phone number, website, offline store, or other payment app; and
- a promotion cue directing the user to transact through that route, from ASR, OCR, or visual signage in video frames.

Do not hit when the host also clearly promotes orders inside TTS, or when traffic redirection has unclear commercial intent.

### Misleading functionality and effect

Hit when exaggerated filming, unrealistic information, or unreliable demonstrations materially magnify product function, effect, size, quality, capacity, or results. The analysis should ask whether the claim is reliable and evidence-supported.

### Dangerous behavior

Hit when content involves violent or unsafe behavior that endangers life safety, including product demonstrations that create a false impression of smoke, fire, or other dangerous effects.

### Disgusting and terrifying

Hit when visual or audio content creates clear discomfort, such as ear cleaning, terrifying atmosphere, insect close-ups, dirty environments such as sewers, sudden screams, or harsh scary sounds.

### Description not detailed

Hit when the video contains product promotion but does not give enough product explanation.

Most products can be acceptable if clearly and fully displayed. Electric and digital products, skincare products, and health supplements must be both displayed and explained.

### Only marketing sales pitches

Hit when verbal or written content is only hard-sell marketing, price, discount, stock pressure, urgency, or buying guidance, and has no substantive product function, specification, usage, effect, material, compatibility, or scenario explanation.

### Pornography perception

Hit when content contains unnecessary exposure or sexually suggestive action, or a product display creates high exposure risk involving sensitive body parts.

Do not hit this label when the content is only ordinary introduction or display of intimate products without nudity involving private parts and without sexually suggestive conduct.

### No physical product display

Hit when the video has verbal or written product explanation but the product is only represented by stickers, cutouts, photos, screenshots, live images, no visible product, or only a partial product view that cannot confirm the bound product.

If the bound product includes package or brand but the video only shows the product result without package or brand, this can also support no physical product display.

### Unrealistic or continuity error

Hit when video frames show physical impossibility, continuity error, product identity drift, structure drift, pattern drift, content identity drift, object materialization, non-physical movement, clipping, garbled morphing text, or unrealistic AIGC display that affects product understanding.

When `is_AIGC` is true, the workflow should pay extra attention to this issue type. It still requires concrete frame evidence.

## Output Schema

The final LLM output must be one JSON object:

```json
{
  "video_id": "",
  "overall_decision": "problematic|manual_review|clean",
  "primary_issue_type": "potential_pirated|irrelevant_promotion|pirated_content|inconsistent_product_promotion|non_native|still_frame|out_of_app_transactions|misleading_functionality_and_effect|dangerous_behavior|disgusting_and_terrifying|description_not_detailed|only_marketing_sales_pitches|pornography_perception|no_physical_product_display|unrealistic_or_continuity_error|none",
  "detected_issue_types": [],
  "is_AIGC": "true|false|unknown",
  "issue_results": {},
  "data_quality": {
    "video_frames_available": true,
    "product_images_available": true,
    "asr_available": true,
    "ocr_available": true,
    "missing_or_weak_inputs": []
  },
  "manual_review_reasons": [],
  "summary_cn": "",
  "final_reason_cn": ""
}
```

`issue_results` must contain one entry for every in-scope issue type:

```json
{
  "potential_pirated": {
    "decision": "hit|no_hit|uncertain",
    "evidence_cn": "",
    "confidence": "high|medium|low"
  }
}
```

`detected_issue_types` is multi-select. `primary_issue_type` is the most important issue for sorting and reporting. `overall_decision` follows:

- `problematic`: one or more issue types have high-confidence hit.
- `manual_review`: evidence is suspicious but incomplete, schema parsing failed, or required evidence is missing for a high-risk claim.
- `clean`: no in-scope issue is supported by available evidence.

## Error Handling

- If `frame_list` is empty, block visual labels such as `still_frame`, `potential_pirated`, `pirated_content`, `unrealistic_or_continuity_error`, `disgusting_and_terrifying`, and visual-only `pornography_perception`.
- If `images` is empty, block strong `inconsistent_product_promotion`; allow `manual_review` if the video mentions a product mismatch but product evidence is missing.
- If ASR/OCR are empty, block strong text-only `only_marketing_sales_pitches`, spoken/written `out_of_app_transactions`, and language-text claims. Visual evidence can still support those labels when visible in frames.
- If `is_AIGC` is missing or invalid, treat it as `unknown`.
- If the LLM returns invalid JSON or illegal labels, Output Validator returns `manual_review` with a schema warning rather than `clean`.

## Testing Plan

1. Input parsing tests:
   - `frame_list` supports newline text and JSON list formats.
   - `images` supports JSON list formats and invalid input fallback.
   - `is_AIGC` supports true, false, and unknown normalization.

2. Evidence Gate tests:
   - Missing frames block visual claims.
   - Missing product images block strong product comparison claims.
   - Missing ASR/OCR blocks text-only hard-sell, off-platform transaction, and language claims.

3. Rules Brain tests:
   - Each in-scope issue type has at least one evidence path that recalls its rule family.
   - `is_AIGC=true` recalls `unrealistic_or_continuity_error` attention only.
   - Pirated and potential pirated rules require strong visual or ASR/OCR evidence and do not trigger from weak montage language alone.

4. Output Validator tests:
   - Strips Markdown code fences.
   - Rejects illegal labels.
   - Fills missing required fields.
   - Preserves multi-select `detected_issue_types`.
   - Keeps malformed risky output as `manual_review`, not `clean`.

## Open Implementation Notes

- Aicolate System Prompt must remain plain text only.
- JSON schema examples and `{{variable}}` references belong in the User Prompt.
- Aicolate Code Node output fields must be added in the Output panel and wired by the same flat names downstream.
- After rule files are created, push them to GitHub and verify both raw URLs before updating the Aicolate HTTP nodes.
