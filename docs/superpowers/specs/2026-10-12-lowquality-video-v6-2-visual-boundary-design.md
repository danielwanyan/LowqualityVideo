# LowqualityVideo v6.2 视觉边界校准设计

日期：2026-10-12
状态：用户已批准方案 2，待书面设计复核后进入实现计划

## 目标

根据 `/Users/bytedance/Downloads/pearl_reviews_2026-10-12.json` 中最新人审结果，同时校准 `still_frame`（静止帧）和 `disgusting_or_terrifying_visual`（恶心恐怖）的规则、Juror C 结构化判断与 `Issue_Level_Finalizer` 硬门槛。

本次设计解决两个根因：

1. 现行规则把静态图片轮播、PPT 式切换和冻结片段也纳入静止帧，宽于最新人审定义。
2. Finalizer 把 Juror C 的底层描述字段当作独立正例信号，可能覆盖主审和 Juror C 的 clean 结论。

## 最新人审依据

- 数据文件：`/Users/bytedance/Downloads/pearl_reviews_2026-10-12.json`
- 文件包含 258 个 case、89 条已保存人审记录和 15 条非空审核备注。
- 本设计使用的目标 diff 共 7 条：
  - 静止帧：sample 35、86、117、193、214。
  - 恶心恐怖：sample 140、173。
- 这 7 条均为目标标签的 false positive。
- 当前已标注数据没有静止帧或恶心恐怖正例，因此本轮只能验证 precision 边界，不能报告这两个标签的 recall。

未保存到 `reviews` 的 case 不作为人审 clean，也不参与本设计的指标或验收。

## 业务定义

### 静止帧

只有当全部可用采样帧在画面内容、构图、角度、颜色、光影、人物姿态、商品位置和商品状态上均无实质变化时，才允许命中 `still_frame`。

以下任一情况都必须阻断 `still_frame`：

- 摄像机或画面角度变化。
- 颜色或光影变化。
- 人物姿态、手部位置或商品位置变化。
- 商品状态或使用步骤变化。
- 不同静态图片之间的切换。
- PPT、图片轮播或 slideshow 展示。
- 虽然单帧看似静态，但跨帧提供了不同商品角度、状态或使用信息。
- 稀疏抽帧无法证明整段画面一致。

不得因为每一张抽样帧本身都是静态图片，就推断原视频是静止帧。

### 恶心恐怖

`disgusting_or_terrifying_visual` 只覆盖强烈、主体性、足以明显引发不适的视觉内容，例如满屏或持续占据主体的严重污垢、虫害或蟑螂、伤口、密集恐惧、恐怖画面，以及大量黏液状或强烈令人不适的处理、拉扯或进食画面。

以下情况必须阻断：

- 清洁用品为了展示清洁前、清洁中或清洁后效果而出现的污垢、脏马桶或类似内容。v6.2 将其设为硬豁免。
- 日历、包装、印刷品或商品图案中的恶趣味、幽默或 novelty 内容。
- 仅局部、短暂或非主体出现的轻微脏污或不美观内容。
- 正常商品演示中的一般不适感。

## Juror C 结构化契约

Juror C 的 Aicolate Input Variables 和 Output Panel 不变。变化只发生在其 `output` JSON 内的 `visual_boundary_check` 字段。

保留现有证据文本字段，并新增：

```json
{
  "all_sampled_frames_effectively_identical": false,
  "meaningful_visual_change_found": true,
  "gross_visual_dominates": false,
  "cleaning_demo_context": false,
  "novelty_or_product_art_context": false,
  "disgusting_visual_threshold_passed": false
}
```

字段语义：

- `all_sampled_frames_effectively_identical`：只有全部采样帧实质一致时为 true。
- `meaningful_visual_change_found`：发现任一角度、颜色、光影、姿态、构图、商品位置或状态变化时为 true。
- `gross_visual_dominates`：强恶心或恐怖画面满屏、居于主体或持续主导视频时为 true。
- `cleaning_demo_context`：脏污用于清洁商品的 before/during/after 演示时为 true。
- `novelty_or_product_art_context`：不适元素属于日历、包装、印刷品、商品图案或幽默恶趣味内容时为 true。
- `disgusting_visual_threshold_passed`：只有达到强度与主体性门槛，且两个语境阻断字段均为 false 时为 true。

旧字段 `static_image_sequence_or_frozen_segments_found` 不再作为业务正例或 Finalizer 候选来源。为避免混合版本放行，即使旧输出仍包含该字段，Finalizer 也必须忽略它。

Juror C 必须保持以下字段一致：

- `visual_boundary_results.still_frame_supported`
- `visual_boundary_results.disgusting_or_terrifying_visual_supported`
- `detected_issue_types`
- 对应 evidence 文本
- 新增结构化 gate 字段
- `overall_decision` 与 `confidence`

## Issue_Level_Finalizer 设计

### 静止帧硬门槛

`still_frame` 只有同时满足以下条件才能通过：

1. 视频帧可用。
2. Juror C 明确设置 `still_frame_supported=true`。
3. `all_sampled_frames_effectively_identical=true`。
4. `meaningful_visual_change_found=false`。
5. `still_frame_evidence` 非空，并逐帧说明为什么全部画面实质一致。
6. Juror C confidence 不低于现有视觉 specialist 门槛。

任一新字段缺失、冲突或不满足时 fail closed，阻断 `still_frame`。主审和 Juror C 的双票不能绕过该硬门槛。

从 `VISUAL_SPECIAL_SIGNAL_TO_ISSUE` 和候选问题收集逻辑中移除 `static_image_sequence_or_frozen_segments_found -> still_frame`。Finalizer 不得在 `still_frame_supported=false` 时根据底层描述字段重新升级该标签。

### 恶心恐怖硬门槛

`disgusting_or_terrifying_visual` 只有同时满足以下条件才能通过：

1. 视频帧可用。
2. Juror C 明确设置 `disgusting_or_terrifying_visual_supported=true`。
3. `disgusting_visual_threshold_passed=true`。
4. `gross_visual_dominates=true`。
5. `cleaning_demo_context=false`。
6. `novelty_or_product_art_context=false`。
7. `vulgar_or_discomfort_evidence` 非空，并说明强度、画面占比和持续性。

任一新字段缺失、冲突或不满足时阻断该标签。主审和 Juror C 的双票不能绕过清洁语境或商品图案语境阻断。

现有 `strong_discomfort_ingestion_visual_found` 可以继续作为候选信号，但不能单独放行；仍需满足上述全部硬门槛。

## 其他组件

### GitHub 规则文件

同时更新：

- `rules/lowquality_video_rules_structured_v1.json`
- `rules/lowquality_video_rules_text_v1.txt`

计划版本：`2026-10-12-v6.2-visual-boundary-human-review`。

规则中删除“static-image sequence、slideshow 或不同静态图切换也可判静止帧”的正例，加入最新静止帧硬定义及恶心恐怖语境阻断。

### Issue_Boundary_Gate_Builder

静止帧 gate 改为要求全部采样帧实质一致，并把任一跨帧视觉变化列为阻断证据。

新增恶心恐怖 gate：要求主体性强不适画面，同时声明清洁演示和 novelty/product-art 为硬阻断。

Input Variables 与 Output Panel 不变。

### 主审、Juror C、Chief Judge

- 主审 Prompt 使用相同业务定义，避免先产生错误候选。
- Juror C Prompt 负责输出新的结构化字段，是视觉硬门槛的主要证据来源。
- Chief Judge Prompt 使用新定义解释 deterministic 结果，但不得覆盖 Finalizer。
- 所有 System Prompt 保持纯文本；JSON schema 和变量引用保留在 User Prompt。

### Chief_JSON_Extractor

输出枚举、排序和字段结构不变，不需要修改。

## 一次一个节点的上线顺序

所有本地文件可以作为一个版本完成和测试，但用户在 Aicolate 画布上继续一次只更新一个节点：

1. Juror C 的 System Prompt 与 User Prompt。
2. `Issue_Level_Finalizer` 完整 Code Node。
3. `SOP_Multimodal_Risk_Reviewer` 的 System Prompt 与 User Prompt。
4. `Issue_Boundary_Gate_Builder` 完整 Code Node。
5. `Lowquality_Chief_Judge` 的 System Prompt 与 User Prompt。
6. 部署 GitHub 规则文件并刷新两个 HTTP rule nodes，确认版本号。

每一步都先运行最小目标 smoke，再进入下一个节点。不得为变量可见性添加冗余画布连线。

## 测试设计

先增加失败测试，再修改实现。

### Finalizer 单元测试

- 旧 `static_image_sequence_or_frozen_segments_found=true` 且 Juror C clean 时不得产生 still_frame 候选。
- 主审和 Juror C 都报 still_frame，但跨帧有实质变化时必须阻断。
- 全部帧实质一致、新字段完整、证据具体且 Juror C 支持时允许 still_frame。
- 清洁演示语境必须阻断 disgusting，即使主审和 Juror C 都支持。
- novelty/product-art 语境必须阻断 disgusting。
- 强烈主体性不适画面且无语境阻断时允许 disgusting。
- 新字段缺失或互相冲突时 fail closed。

### 规则与 Prompt 契约测试

- 禁止旧 slideshow/static-image-sequence 正例文案重新出现。
- 要求静止帧和恶心恐怖新字段出现在 Juror C schema 与 Prompt。
- 要求清洁场景和商品图案阻断同时存在于规则、主审、Juror C、Chief 和 boundary gate。
- 确保其他 11 个标签、优先级和输出 schema 不变。

### Aicolate 回归样本

- sample 35、86、193、214：预期 clean。
- sample 117：只保留 `pure_marketing_pitch`。
- sample 140、173：预期 clean。

当前 reviewed 数据没有这两个标签的正例。Aicolate 回归报告必须明确这一限制，不能把未标注样本当成 recall 证据。

## 验收标准

- 本地现有规则与 selective-jury 测试全部通过。
- 新增 Visual Boundary 测试全部通过。
- 7 个目标 case 的输出符合上述预期。
- 所有输出 JSON 可解析，primary label 与完整 issue list 继续遵守既定优先级。
- 不改变 `is_aigc` 契约、其他标签定义、Start 输入或 End 输出路径。
- Aicolate 操作说明继续提供完整可粘贴内容、准确 Input Variables 和 Output Panel，并一次只交付一个节点。

## 非目标

- 本轮不处理 sample 7/100 的疑似盗剪 UI 边界。
- 本轮不处理 sample 33/85 的挂车商品不一致漏召回。
- 本轮不增加图像相似度 RPC、视频解码或新的 Aicolate 节点。
- 本轮不修改标签优先级和最终输出 schema。
