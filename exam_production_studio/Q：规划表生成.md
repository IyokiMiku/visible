# Q：规划表生成问题总结

> 记录于 2026-07-01。目的：说明 studio 现有规划表链路与《一课一练 规划表编写说明.md》的差距，以及它如何导致一课一练命名无法按权威版式完成。

## 一、结论速览

- studio 的规划表链路**整体没和《规划表编写说明.md》对齐**，属于“未实现/未对齐”，不是单点崩溃式 bug。
- 三个环节都有问题：**教材目录扫描（数据源）→ 规划生成/解析 → 数据模型**，且彼此**数据没接上**。
- 后果：一课一练**正文三行标题无法按权威版式生成**（尤其第 3 行的“第X单元…第Z章…第W节…”）。文件名基本能拼出来。

## 二、studio 现有规划链路（现状）

一课一练 flow 节点：`读取资料 → 解析目录 → 生成规划 → 知识点匹配 → 拉题与补题 → 质检导出 → 内容审阅 → 格式装配`
（`backend/engine/drivers/yikeyilian.py` + `backend/engine/runner.py`）。

1. **解析目录**（`kpoint_count` → `scan_textbook_toc`，`backend/shared/ocr/scanner.py`）
   - 只产出一个**纯文本 md**（`_教材目录扫描结果.md`）：优先读 PDF 内置书签，无书签则抽前 5 页文本片段。
   - **不结构化**、不产 `toc_structured.json`。

2. **生成规划**（`planning.gen_planning`，`backend/engine/steps/planning.py`）
   - 上传则 `_parse_uploaded`，否则 `_synthesize`（本地合成占位）。
   - 表头：`["序号", "卷号", "试卷主题", "考纲知识点", "卷型", "难度", "套数"]`。
   - `_parse_uploaded` 只提取 `试卷主题`(topic) 与 `考纲知识点`(point_name)，练号用行计数 `enumerate(...,1)`，忽略 A 列序号。

3. **落库**（`papers` 表，`backend/db.py`）
   - 字段：`id / project_id / paper_no / paper_type / module / topic / point_name / kpoint_id / status / docx_paths / qc_report_path`。
   - **无** 单元/章/节、级别、考纲标号、meta JSON 字段。

## 三、与权威规划表规范的差距（核心问题）

| # | 问题 | 现状 | 权威规范要求 |
|---|---|---|---|
| 1 | **数据源断裂** | `scan_textbook_toc` 只写 md，`planning.py` **完全不读**它 | 教材目录 → 结构化 → 驱动规划（§7.2） |
| 2 | **合成是占位** | `_synthesize` 造“课程 第i练主题”假数据，无层级 | 目录驱动，主题来自教材目录 |
| 3 | **解析不认层级** | 认第 1 行为表头、其余全当平铺数据行，用行号当练号 | 课程行/单元行(一级)/章行(二级) 合并行 + 考点行，练号取 A 列序号（§2.4/§2.6） |
| 4 | **列不一致** | 序号/卷号/试卷主题/考纲知识点/卷型/难度/套数 | A序号/B考纲知识点/C试卷主题/D级别/E题型/F难度/G套数/H考纲标号（§2.2） |
| 5 | **数据模型缺字段** | papers 只有 topic/point_name/module | 需 单元名/号、章名/号、节号、级别、考纲标号 |
| 6 | **级别逻辑缺失** | 无“极重要/重要/标准”，无极重要拆两行（一）（二） | §4.3/§5.1 硬性要求 |

## 四、接口层问题（有，且是关键卡点）

不是 HTTP 接口坏了，而是**内部数据契约（接口签名/行结构）没有承载层级的槽位**，即使解析出层级也传不下去：

1. `gen_planning(ctx, source) -> (Path, rows)`：`rows` 每条只有 `{paper_no, topic, point_name, paper_subtype, difficulty, status}`，**没有 unit/chapter/section/level 字段**。
2. `assemble(ctx, paper_no, qs)`（`backend/engine/steps/assemble.py`）取名只用 `topic`：
   `paper_name = paper.get("topic") or qs.meta.get("topic") or ctx.course`，再传给 `generate_docx(..., paper_name=paper_name, topic=paper_name)`。
3. `build_title_lines(ctx, paper_no, *, paper_name, paper_subtype, suffix, topic)`（`backend/shared/docx/naming.py`）：**签名里没有单元/章/节参数**，一课一练分支只用 province/textbook/edition/topic。
4. `scan_textbook_toc` 的产物**没有接口被 planning 调用**（数据流断点）。

## 五、一课一练命名能否完成？

分两层看：

- **文件名**：**能**。`name_template` 用到的字段都齐
  （`第{vol}练 {topic} {province}（{exam_type_name}）《{textbook}》（{edition}） 一课一练 （{variant}）`），与成品文件名规则基本一致。
- **正文三行标题**：**当前不能完整完成**。现在会产出一个三行标题（流程不报错、能出 docx），但和权威版式三处不符：
  - 行1 缺（考试类型）；
  - 行2 缺“第x练”且版次没括号；
  - **行3 完全没有“第X单元…第Z章…第W节…”层级**。
- **根因**：数据源（目录未结构化/未消费）→ 数据模型（无层级字段）→ 标题函数（无汉字序号转换、无三级拼接）三层全断。**要先把规划链路对齐，命名才可能完整完成。**

### 权威正文标题版式（目标）

```text
省份（考试类型）一课一练
《教材名》（出版社·版次） 第y练
第X单元 一级标题名称 第Z章 二级标题名称 第W节 试卷主题
```

- 单元/章/节用**中文大写序号**（第一单元/第一章/第一节）；练号 `第y练` 用 **A 列序号（阿拉伯）**。
- 一级标题=单元名，二级标题=章名，节名=C 列试卷主题。
- 参考旧工具包 `docx_generation.py` 的 `_number_to_cn / _strip_unit_title / _parse_section_title / _format_section_title`，含无 `unit` 时的“两级降级”分支。

示例：

```text
内蒙古自治区（对口招生）一课一练
《电子技术基础与技能》（高教版·第四版） 第1练
第一单元 二极管及其应用 第一章 二极管基础知识 第一节 二极管的结构与特性
```

## 六、要对齐需要改什么（实现清单）

1. `scan_textbook_toc` 输出**结构化目录**（单元/章/节层级 + 页码），或至少产 `toc_structured.json`。
2. 重写 `planning._parse_uploaded`：按 §2 层级行状态机解析（追踪当前单元/章），考点行取 A 列序号，记录 单元名/号、章名/号、节号、C 列主题、级别(D)、考纲标号(H)；未显式编号按出现顺序自动编号；极重要拆两行（一）（二）。
3. `_synthesize` / 目录驱动：让本地路径也能产层级（或明确要求上传标准 xlsx）。
4. **扩展数据契约**：`gen_planning` 的 row、`papers` 表（新增列或加 meta JSON）、`ctx`/`qs.meta`、`build_title_lines` 签名，全部补上层级字段。
5. 移植旧工具包 `_number_to_cn / _format_section_title`，重写 `build_title_lines` 一课一练分支为三行版式（单元/章/节汉字、练号阿拉伯），含两级降级分支。
6. 同步 `configs/yikeyilian/编写规范.md` §十一/§十二，并修掉“章节前缀/书名号”不一致。

## 七、前置决策（实现前需拍板）

- **规划表来源策略**：强制上传符合《规划表编写说明.md》的标准 xlsx？还是把本地教材目录扫描也做成结构化驱动（工作量更大）？
- OCR/合成路径在拿不到层级时的降级策略：走“两级标题模板”，还是直接要求补数据后再生成。

---

_相关文件：_
- _studio：`backend/engine/steps/planning.py`、`backend/shared/ocr/scanner.py`、`backend/engine/steps/assemble.py`、`backend/shared/docx/naming.py`、`backend/db.py`、`backend/engine/runner.py`_
- _权威规范：`一课一练工具包（含示例）/.../05_项目文档（使用前必读！）/规划表编写说明.md`_
- _权威标题逻辑：`一课一练工具包（含示例）/.../01_工具脚本/生成器/docx_generation.py`_
