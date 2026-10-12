# LowqualityVideo v6.2 Visual Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broad static-slideshow and generic-discomfort rules with reviewed hard gates for `still_frame` and `disgusting_or_terrifying_visual`, then provide a one-node-at-a-time Aicolate update guide.

**Architecture:** Juror C emits explicit structured boundary facts, and `Issue_Level_Finalizer` treats those facts as mandatory hard gates instead of allowing low-level signals or reviewer consensus to bypass the business definition. HTTP rule files, all reviewing prompts, the boundary packet, tests, and the durable Aicolate copybook are updated together while preserving the existing workflow topology and output schema.

**Tech Stack:** Python 3 standard library, `unittest`, JSON rule files, plain-text Aicolate prompts, Markdown operator guides.

---

## File map

Tracked rule repository:

- Modify: `rules/lowquality_video_rules_structured_v1.json` — v6.2 structured business definitions.
- Modify: `rules/lowquality_video_rules_text_v1.txt` — v6.2 human-readable HTTP rule source.
- Modify: `tests/test_rules_files.py` — rule-version and boundary regression tests.
- Create: `docs/superpowers/plans/2026-10-12-lowquality-video-v6-2-visual-boundary.md` — this implementation plan.

Active Aicolate copybook under `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/aicolate_selective_jury`:

- Modify: `code_nodes/issue_level_finalizer.py` — mandatory still-frame and disgusting-visual gates.
- Modify: `code_nodes/issue_boundary_gate_builder.py` — matching boundary packet.
- Modify: `prompts/sop_multimodal_risk_reviewer_system_prompt.txt` — main-reviewer definitions.
- Modify: `prompts/juror_c_visual_boundary_checker_system_prompt.txt` — visual specialist definitions.
- Modify: `prompts/juror_c_visual_boundary_checker_user_prompt.txt` — new structured output fields and procedure.
- Modify: `prompts/chief_judge_system_prompt.txt` — deterministic explanation boundary.
- Modify: `prompts/chief_judge_user_prompt.txt` — deterministic explanation boundary.
- Modify: `tests/test_selective_jury_local_artifacts.py` — Finalizer and prompt contract regressions.
- Modify: `ACTIVE-ARTIFACTS.md` — active version and operator guide pointer.
- Create: `LowqualityVideo-v6.2-Visual-Boundary-Aicolate-Update-Guide-2026-10-12.md` — exact one-node-at-a-time instructions.

Wiki rule mirrors:

- Modify: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/rules/lowquality_video_rules_structured_v1.json`.
- Modify: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/rules/lowquality_video_rules_text_v1.txt`.

No Start input, canvas edge, Aicolate Input Variable, Output Panel, `Chief_JSON_Extractor`, label priority, or End mapping changes are allowed.

### Task 1: Add failing Finalizer regression tests

**Files:**

- Modify: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/aicolate_selective_jury/tests/test_selective_jury_local_artifacts.py`

- [ ] **Step 1: Replace the obsolete special-signal recovery expectation**

Remove `still_frame` from `test_issue_level_finalizer_recovers_reviewed_visual_special_signals`. Keep the continuity special signal. Replace the disgusting case with a separate hard-gate positive test in Step 3.

- [ ] **Step 2: Add still-frame false-positive tests**

Add tests with the existing `DummyArgs`, `load_issue_level_finalizer`, and JSON helpers:

```python
def test_issue_level_finalizer_ignores_legacy_static_sequence_signal_when_juror_is_clean(self):
    module = load_issue_level_finalizer()
    juror_c = {
        "overall_decision": "clean",
        "primary_issue_type": "none",
        "detected_issue_types": [],
        "confidence": 1.0,
        "visual_boundary_check": {
            "still_frame_evidence": "不同静态图片之间发生切换",
            "static_image_sequence_or_frozen_segments_found": True,
        },
        "visual_boundary_results": {"still_frame_supported": False},
    }
    result = asyncio.run(module.main(DummyArgs({
        "main_reviewer_json": "{}",
        "juror_a_json": "{}",
        "juror_b_json": "{}",
        "juror_c_json": json.dumps(juror_c, ensure_ascii=False),
        "video_data_quality_json": '{"video_frames_available":true}',
    })))
    self.assertEqual(result["deterministic_primary_issue_type"], "none")


def test_issue_level_finalizer_blocks_still_frame_when_meaningful_change_exists(self):
    module = load_issue_level_finalizer()
    reviewer = {
        "overall_decision": "problematic",
        "primary_issue_type": "still_frame",
        "detected_issue_types": ["still_frame"],
    }
    juror_c = dict(reviewer, confidence=0.99)
    juror_c["visual_boundary_check"] = {
        "still_frame_evidence": "帧间有角度、光影和姿态变化",
        "all_sampled_frames_effectively_identical": False,
        "meaningful_visual_change_found": True,
    }
    juror_c["visual_boundary_results"] = {"still_frame_supported": True}
    result = asyncio.run(module.main(DummyArgs({
        "main_reviewer_json": json.dumps(reviewer),
        "juror_a_json": "{}",
        "juror_b_json": "{}",
        "juror_c_json": json.dumps(juror_c),
        "video_data_quality_json": '{"video_frames_available":true}',
    })))
    self.assertEqual(result["deterministic_primary_issue_type"], "none")
```

Add a positive counterpart where `all_sampled_frames_effectively_identical=true`, `meaningful_visual_change_found=false`, Juror C supports the issue, evidence is non-empty, and confidence is `0.95`; expect `still_frame`.

- [ ] **Step 3: Add disgusting-visual context tests**

Add three tests using the same Finalizer entry point:

1. Main and Juror C both support disgusting, but `cleaning_demo_context=true`; expect clean.
2. Main and Juror C both support disgusting, but `novelty_or_product_art_context=true`; expect clean.
3. Juror C supports disgusting with `disgusting_visual_threshold_passed=true`, `gross_visual_dominates=true`, both context blockers false, evidence non-empty, and confidence `0.95`; expect `disgusting_or_terrifying_visual`.

Each Juror C payload must include:

```python
"visual_boundary_results": {
    "disgusting_or_terrifying_visual_supported": True,
},
"visual_boundary_check": {
    "vulgar_or_discomfort_evidence": "强烈不适画面持续占据主体",
    "gross_visual_dominates": True,
    "cleaning_demo_context": False,
    "novelty_or_product_art_context": False,
    "disgusting_visual_threshold_passed": True,
},
```

- [ ] **Step 4: Run the selective-jury tests and confirm RED**

Run from the active copybook directory:

```bash
python3 -m unittest discover -s tests -p 'test_selective_jury_local_artifacts.py'
```

Expected: failures showing that the legacy static signal still upgrades clean, meaningful changes do not hard-block still-frame, and cleaning/product-art contexts do not hard-block disgusting.

### Task 2: Implement Finalizer hard gates

**Files:**

- Modify: `/Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/aicolate_selective_jury/code_nodes/issue_level_finalizer.py`

- [ ] **Step 1: Remove the legacy still-frame special signal**

Change:

```python
VISUAL_SPECIAL_SIGNAL_TO_ISSUE = {
    "impossible_hand_object_interaction_found": "unrealistic_or_continuity_error",
    "strong_discomfort_ingestion_visual_found": "disgusting_or_terrifying_visual",
}
```

Do not retain `static_image_sequence_or_frozen_segments_found` anywhere in candidate collection or pass logic.

- [ ] **Step 2: Parse and expose the new hard-gate fields**

Inside `_evaluate_visual_issue`, read both field presence and boolean values:

```python
identical_field_present = "all_sampled_frames_effectively_identical" in visual_check
all_frames_identical = _bool(visual_check.get("all_sampled_frames_effectively_identical"))
change_field_present = "meaningful_visual_change_found" in visual_check
meaningful_change_found = _bool(visual_check.get("meaningful_visual_change_found"))

gross_dominates_field_present = "gross_visual_dominates" in visual_check
gross_visual_dominates = _bool(visual_check.get("gross_visual_dominates"))
cleaning_context_field_present = "cleaning_demo_context" in visual_check
cleaning_demo_context = _bool(visual_check.get("cleaning_demo_context"))
novelty_context_field_present = "novelty_or_product_art_context" in visual_check
novelty_or_product_art_context = _bool(
    visual_check.get("novelty_or_product_art_context")
)
disgusting_threshold_field_present = "disgusting_visual_threshold_passed" in visual_check
disgusting_threshold_passed = _bool(
    visual_check.get("disgusting_visual_threshold_passed")
)
```

Add all values and `*_field_present` diagnostics to `gate_details`.

- [ ] **Step 3: Apply mandatory still-frame conditions**

Before returning the visual gate, set `gate["passed"]=False` and add an opposing reason unless every required condition holds:

```python
if issue == "still_frame":
    still_hard_gate = (
        structured_supported
        and juror_supports
        and identical_field_present
        and all_frames_identical
        and change_field_present
        and not meaningful_change_found
        and bool(structured_evidence)
        and juror_confidence is not None
        and juror_confidence >= 0.85
    )
    if not still_hard_gate:
        gate["passed"] = False
        _add_oppose(
            gate,
            "issue_level_finalizer",
            "still_frame requires explicit all-frame identity and no meaningful visual change",
        )
```

This hard gate applies even when main and Juror C both vote problematic.

- [ ] **Step 4: Apply mandatory disgusting-visual conditions**

Implement an equivalent hard gate:

```python
if issue == "disgusting_or_terrifying_visual":
    disgusting_hard_gate = (
        structured_supported
        and juror_supports
        and gross_dominates_field_present
        and gross_visual_dominates
        and cleaning_context_field_present
        and not cleaning_demo_context
        and novelty_context_field_present
        and not novelty_or_product_art_context
        and disgusting_threshold_field_present
        and disgusting_threshold_passed
        and bool(structured_evidence)
        and juror_confidence is not None
        and juror_confidence >= 0.85
    )
    if not disgusting_hard_gate:
        gate["passed"] = False
        _add_oppose(
            gate,
            "issue_level_finalizer",
            "disgusting visual requires dominance and blocks cleaning or novelty/product-art context",
        )
```

- [ ] **Step 5: Run the selective-jury tests and confirm GREEN**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_selective_jury_local_artifacts.py'
```

Expected: all tests pass after updating any old positive fixtures to include the new mandatory fields.

### Task 3: Update the visual-review prompts and boundary packet

**Files:**

- Modify: active Juror C system/user prompts.
- Modify: active main-reviewer system prompt.
- Modify: active Chief Judge system/user prompts.
- Modify: active `issue_boundary_gate_builder.py`.
- Modify: active selective-jury test file.

- [ ] **Step 1: Add failing prompt-contract assertions**

Replace assertions that require `static-image sequence` as a positive still-frame rule. Assert instead that the main, Juror C, and Chief prompts contain:

```text
all sampled frames
meaningful visual change
slideshow
cleaning demonstration
novelty or product art
```

Assert that the Juror C user schema contains all six new JSON field names and that the old field is absent.

Assert that `issue_boundary_gate_builder.py` contains `all_sampled_frames_effectively_identical`, `meaningful_visual_change_found`, `cleaning_demo_context`, and `novelty_or_product_art_context`.

Run the selective-jury suite and confirm these assertions fail before editing the artifacts.

- [ ] **Step 2: Rewrite the still-frame policy consistently**

In the main, Juror C, and Chief prompts:

- Require all available sampled frames to remain effectively identical.
- State that any content, composition, angle, color, lighting, pose, hand, product-position, or product-state change blocks still-frame.
- Explicitly state that slideshow/PPT/different-image switching is clean.
- State that sparse frames default to clean when full-video immobility cannot be established.
- Remove all positive slideshow/static-image-sequence language.

- [ ] **Step 3: Rewrite the disgusting-visual policy consistently**

In the same prompts:

- Require strong discomfort to dominate or fill the visual presentation.
- Hard-block cleaning-product before/during/after demonstrations.
- Hard-block novelty, humor, calendar, packaging, printed, or product-art contexts.
- Preserve severe infestation, injury, dense-phobia, horror, and dominant viscous/ingestion positives.

- [ ] **Step 4: Update Juror C JSON schema and process**

Add the six new booleans exactly as specified in the design. Require internal consistency between evidence, booleans, `visual_boundary_results`, labels, and decision.

Remove `static_image_sequence_or_frozen_segments_found` from the output schema and procedure.

- [ ] **Step 5: Update Issue_Boundary_Gate_Builder**

The `still_frame` gate must require:

```python
"required_evidence": [
    "all_sampled_frames_effectively_identical",
    "meaningful_visual_change_found=false",
    "concrete_all-frame_comparison",
],
"blocked_evidence": [
    "content_shift",
    "composition_shift",
    "angle_shift",
    "color_shift",
    "lighting_shift",
    "pose_shift",
    "hand_or_product_position_shift",
    "product_state_change",
    "slideshow_or_different_image_sequence",
],
```

Add a `disgusting_or_terrifying_visual` gate requiring visual dominance and blocking cleaning/product-art context.

- [ ] **Step 6: Run the selective-jury suite**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all selective-jury tests pass.

### Task 4: Update and mirror the v6.2 HTTP rules

**Files:**

- Modify: tracked structured and text rules.
- Modify: tracked `tests/test_rules_files.py`.
- Modify: the two Wiki rule mirrors.

- [ ] **Step 1: Write failing v6.2 rule assertions**

Change the expected version to:

```text
2026-10-12-v6.2-visual-boundary-human-review
```

For V13, assert all-frame identity is required and slideshow is a false-positive boundary, not a trigger. For V9, assert cleaning demonstration and novelty/product-art are false-positive boundaries and dominance is required.

Run:

```bash
python3 -m unittest discover -s tests -p 'test_rules_files.py'
```

Expected: failures on version and new boundary text.

- [ ] **Step 2: Modify the structured rules**

Set the v6.2 version. Replace V13 triggers and false-positive boundaries with the approved strict definition. Add V9 dominance and context boundaries. Keep issue types, priority, evidence contract, and output contract unchanged.

- [ ] **Step 3: Modify the text rules**

Update the title/version and V9/V13 prose to match the structured rules exactly in meaning. Remove all text that treats a slideshow or static-image sequence as a still-frame positive.

- [ ] **Step 4: Mirror both rule files**

The tracked rule files and Wiki rule files must be byte-identical. Verify with `cmp -s`.

- [ ] **Step 5: Run tracked repository tests**

Run from `/Users/bytedance/LowqualityVideo`:

```bash
python3 -m unittest discover -s tests
```

Expected: all tests pass with only the repository's existing intentional skips.

### Task 5: Create the v6.2 Aicolate operator guide

**Files:**

- Create: active `LowqualityVideo-v6.2-Visual-Boundary-Aicolate-Update-Guide-2026-10-12.md`.
- Modify: active `ACTIVE-ARTIFACTS.md`.

- [ ] **Step 1: Document the exact node order**

The guide must instruct the user to update exactly one node at a time:

1. Juror C system and user prompts.
2. `Issue_Level_Finalizer` full code.
3. Main reviewer system and user prompts.
4. `Issue_Boundary_Gate_Builder` full code.
5. Chief Judge system and user prompts.
6. Refresh both HTTP rule nodes and verify the v6.2 version.

- [ ] **Step 2: Document unchanged contracts**

For every changed node, list the current Input Variables and Output Panel exactly. State that no canvas edge, Start input, End output, or Chief extractor change is required.

- [ ] **Step 3: Document smoke checks**

List expected outputs:

- 35, 86, 193, 214 -> clean.
- 117 -> only `pure_marketing_pitch`.
- 140, 173 -> clean.
- A synthetic all-identical-frame case -> `still_frame`.
- A synthetic dominant severe-discomfort case without blockers -> `disgusting_or_terrifying_visual`.

State that the reviewed file has no positive human examples for these two labels, so recall is not measurable from this batch.

- [ ] **Step 4: Update ACTIVE-ARTIFACTS**

Set current version to v6.2 and point the active operational guide to the new file.

### Task 6: Full verification and handoff

- [ ] **Step 1: Run both test suites**

```bash
cd /Users/bytedance/LowqualityVideo
python3 -m unittest discover -s tests
```

```bash
cd /Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/aicolate_selective_jury
python3 -m unittest discover -s tests
```

Expected: both suites pass. Record exact counts from command output.

- [ ] **Step 2: Run consistency checks**

```bash
git -C /Users/bytedance/LowqualityVideo diff --check
cmp -s /Users/bytedance/LowqualityVideo/rules/lowquality_video_rules_structured_v1.json /Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/rules/lowquality_video_rules_structured_v1.json
cmp -s /Users/bytedance/LowqualityVideo/rules/lowquality_video_rules_text_v1.txt /Users/bytedance/Desktop/EU-LLM_Wiki/wiki/projects/lowquality-video/rules/lowquality_video_rules_text_v1.txt
```

Expected: no whitespace errors and both comparisons return zero.

- [ ] **Step 3: Commit tracked repository changes**

Stage only the plan, rule files, and tracked tests. Commit with a focused message. Do not stage unrelated user changes.

- [ ] **Step 4: Deliver the first Aicolate node**

Following the operator guide, provide the complete Juror C System Prompt and User Prompt file paths, confirm Input Variables and Output Panel are unchanged, and wait for the user to update that node before delivering `Issue_Level_Finalizer`.
