# 题库/API 拉题策略

本文件只在生成试卷、预评估覆盖率或排查 API 拉题问题时读取。

## 主流程

`api_to_paper.py` 负责从本地题库和学科网 API 选题，随后调用 `paper_builder.py` 生成 DOCX。

执行顺序：

1. 校验本卷 config 能从省份管理解析。
2. 加载 `output/bank/《课程》/{choice,fill,judge,short,comp}.json`。
3. 按 `kpoint_ids` 和题型筛选。
4. 排除 `_used.json` 已用题和 `_errata.json` 已标记错题；两者只在选题过滤时合并，保存 `_used.json` 时只记录本卷实际选中的题。
5. 本地不足时调 API 拉题并追加入库。
6. 仍不足时输出缺题需求，由 AI 补齐。
7. 更新 `_used.json`。
8. 生成 `volXX_ids.json` 或 `volXX_paper.json`，再生成 DOCX。

## 预评估

每卷出卷前先运行 `--assess`，生成 `coverage_assessment.json`。预评估用于判断题库覆盖，不生成 DOCX。

预评估应同时区分题库总命中数、错题阻断数和实际可用数，避免把错题阻断造成的下降误判为 API 或题库本身缺题。

网络/API/Cookie/appKey/sign 失败时，先修环境；不要把访问失败当作题库缺题。

## 拉题策略

| 题型 | 策略 | 倍率 | 说明 |
|------|------|------|------|
| 综合/计算/作图题 | 扫尽全部页面 | 5x | 压轴题质量敏感，尽量拉满候选 |
| 简答题 | 随机翻页 + 多级回退 | 5x | 多拉候选，人工/脚本筛选 |
| 选择/判断/填空 | 随机翻页 + 多级回退 | 3x | 保持多样性并避免固定第 1 页重复 |

随机翻页回退：

| Level | 页码范围 | 行为 |
|-------|----------|------|
| 0 | 1-20 | 随机 3 页 |
| 1 | 1-11 | 随机 3 页，去重 |
| 2 | 1-6 | 随机 3 页，去重 |
| 3 | 未试页 | 顺序遍历 |

连续 6 页空时跳到 Level 3。

## 范围约束

- 考点训练卷不做跨知识点降级拉题；不足交 AI 补题。
- 专题训练卷和课程综合卷缺题时按题型分化策略拉题，缺额交 AI 补题。
- 已移除跨课程全库搜索降级；跨课程拉题属于脱纲风险。
- 使用叶子 `kpoint_ids` 时传 `--no-expand`。
- 父节点仅在全部子节点都属于本卷范围时可用。
- `_errata.json` 中 `selection_blocked=true` 的题号不得再次选入新卷；把 `selection_blocked` 改为 `false` 后可恢复选用。
- 读取 `_errata.json` 时兼容 `question_id` 和 API 原始字段 `questionId`；`selection_blocked` 兼容字符串形式的 `"false"`、`"0"`、`"no"`、`"off"`。
- `status=ignored` 不阻断选题；`status=fixed` 只表示当前卷修复完成，不自动解除阻断。
- `_errata_index.json` 是全项目汇总视图，由各课程 `_errata.json` 同步生成，不直接手工编辑：

```bash
python 01_工具脚本/学科网API拉题移植版/api_pull_core.py --sync-errata-index --bank-root "题库根目录"
```

## 入库过滤

拒绝以下题目：

| 条件 | 原因 |
|------|------|
| `status != 1` | 状态异常 |
| `kpointIds` 为空 | 无知识点标签 |
| `difficulty` 缺失 | 无难度值；`0` 是合法难题，不拒绝 |
| 答案既无文字也无图片，或仅为“略” | 无有效答案 |
| 题干极短且无配图 | 残题风险 |
| 选择题答案非 A-D | 答案格式错误 |
| 判断题答案非 正确/错误 | 答案格式错误 |

以下情况不再硬拒绝，只写入 `_quality_flags`、`_quality_layer`、`_quality_score`，选题时按层级降低优先级：

| 层级 | 含义 | 常见标签 |
|------|------|----------|
| A | 完整题，优先使用 | 无标签 |
| B | 题目和答案完整，但无解析 | `no_explanation` |
| C | 短题干但语义明确 | `short_stem` |
| D | 答案图片型，适合机械制图作图/综合题 | `answer_image_only` |
| E | 弱质量兜底 | `weak_answer_text`、`ai_style_stem` 等 |

机械制图作图题常见“答案只有图片”，必须视为可用题；不能因为清理 HTML 后答案文字为空而拒绝。

## 手工预拉题

只有需要加速首卷或排查 API 时使用 `query_questions.py`。`--merge-to` 追加合并，不覆盖已有题库，按 `questionId` 去重。
