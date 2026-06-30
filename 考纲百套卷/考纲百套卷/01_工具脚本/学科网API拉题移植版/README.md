# 学科网 API 拉题移植版

本文件夹是 `考纲百套卷` 项目内的 API 拉题工具，放在 `01_工具脚本` 下。

## 与主流程的关系

**已接入主流程的函数**（模式 2——API 拉题模式中由 `runner.py` 调用）：

| 文件 | 函数 | 用途 |
|---|---|---|
| `query_questions.py` | `query_questions`, `build_payload` | API 请求封装，按 courseId/typeId/kpointIds/difficulty 拉题 |
| `kpoint_resolver.py` | `load_mapping_table` | 加载 .xlsx 映射表 |
| `kpoint_resolver.py` | `resolve_course` | 根据规划表课程名 → courseId |
| `kpoint_resolver.py` | `resolve_type` | 根据规划表题型名 → typeId |
| `kpoint_resolver.py` | `get_mapping_ai_generate_papers` | 识别 AI 生成/聚合卷 |
| `api_pull_core.py` | `apply_content_filter` | 入库过滤（状态、知识点、难度、答案有效性） |
| `html_content_converter.py` | `convert_html_to_text` | HTML/QML 内容 → 纯文本 |

**独立调试/手工工具**（未接入主流程，可用于排查或手工补题）：

| 文件 | 函数 | 说明 |
|---|---|---|
| `api_pull_core.py` | `pull_for_section()` | 单题型拉题入口 |
| `api_pull_core.py` | `random_page_pull()`, `pull_all_pages()` | 普通题型与综合题的拉题策略 |
| `api_pull_core.py` | `classify_question()` | 简答/综合错标题的重分类 |
| `api_pull_core.py` | `save_bank_items()` | 去重、过滤、写入本地题库 |
| `kpoint_type_summary.py` | — | 知识点题型汇总统计 |
| `update_type_counts.py` | — | 更新题型计数 |

## 文件说明

| 文件 | 作用 |
|---|---|
| `query_questions.py` | get-question-list API 调用；Cookie 改为从 `config.json` 读取。 |
| `api_pull_core.py` | 拉题策略（随机翻页、综合题扫页、入库过滤、题型重分类、错题阻断、去重）；`apply_content_filter` 已接入主流程。 |
| `kpoint_resolver.py` | 课程/题型/知识点映射解析；映射表加载和 AI 补题卷识别已接入主流程。 |
| `html_content_converter.py` | HTML/QML → 纯文本与 LaTeX 转换；`convert_html_to_text` 已接入主流程。 |
| `api_reference.md` | API 参数、鉴权、返回字段说明。 |
| `api-selection.md` | v2 中原有的拉题策略说明。 |
| `kpoint_type_summary.py` | 知识点题型汇总（独立工具）。 |
| `update_type_counts.py` | 更新题型计数（独立工具）。 |

## 鉴权

Cookie 从 `config.json` 的 `xkw_cookie` 字段读取，无需环境变量。

## 错题阻断与索引

每个课程题库目录可以放 `_errata.json`。拉题时读取同目录 `_errata.json`，把 `selection_blocked=true` 且 `status!=ignored` 的题号加入本次排除集合。

生成项目级汇总索引：

```bash
python 01_工具脚本/学科网API拉题移植版/api_pull_core.py \
  --sync-errata-index \
  --bank-root "题库根目录"
```

## 单页查询示例

```bash
python query_questions.py \
  --course-id 1093 \
  --type-ids 1000001 \
  --kpoint-ids 123456 \
  --page-size 10 \
  --summary
```
