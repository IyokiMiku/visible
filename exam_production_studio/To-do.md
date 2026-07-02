# To-do

## 通用

- [x] 1. 规划表读的卷数不对（已修：口径统一到三类卷全局编号——`_gen_kaogang` 现落考点卷+专题卷+综合卷（全局卷号 1..N），`runner.total=len(papers)`/向导/范围校验随之按 N；并补 `ctx.selected_papers(total)` 全局卷号范围筛选。详见下方 P2/P1）
- [ ] 2. 规划表生成流程建立（后端已建：PDF类型判定/结构化目录/8列一课一练解析·渲染·三行标题/10列考纲百套卷解析·卷号编排/映射分层聚合/细目表/校验器/LLM生成编排/闸门写回接口，均已验证；未完成：前端可编辑闸门页 + LLM实调 + runner串接两闸门。详见《规划表生成-步骤.md》）
- [ ] 3. OCR 扫描后需要有人工复核的一步（未完成：闸门1 后端/前端组件（`gates.py`/`Gates.vue`）已就绪，但未串进 runner 成为复核暂停点，步骤文档 E1 待联调；详见下方 P3）
- [ ] 4. 分清楚必须和不必须的文件，上传后有明显的显示（未完成：必传校验（前端 `REQUIRED_KINDS`/`validateRequiredUploads`）+ 后端类型白名单 `ALLOWED_EXTS` 已做；缺「上传后 UI 明显标出 必传/已传/缺失 状态」）
- [ ] 5. 改一课一练和考点双析卷的编写规范（考点双析卷已完成，并对齐卷首版式 + 配套改代码/前端；未完成：一课一练待改 §十一/§十二 标题为权威三级版式「省份（考试类型）一课一练 / 《教材》（出版社·版次）第 x 练 / 第 X 单元 一级标题 第 Z 章 二级标题 第 W 节 主题」，且真正生成该版式依赖规划表链路对齐，详见 `Q：规划表生成.md`）
- [ ] 6. 识别哪里用视觉模型自己扫描然后给人工判断作为规划表生成依据（或者 RAG 切片，总之就是调 LLM + ???）（未完成：渲染/gating 框架已就绪，但 `vision.py` 实调待凭据、OCR 模型待定，步骤文档 A3/F1）
- [ ] 7. AI 匹配映射表有问题（未完成：`mapping.py` 已接分层聚合（`_gen_mapping_kaogang`），但 AI 匹配准确性依赖 LLM 实调（未通），原「有问题」是否已解决未验证）
- [ ] 8. 确认课程量（规划表读取，可人工修改）（未完成：`kpoint_count.py` 题量为占位「待统计」，缺「读取真实课程量 + 人工修改」的实现）

## 资源导入界面

- [ ] 1. 在项目创建完成后，改成在界面上方加横向进度条，不在左侧边栏显示；边栏应该显示不同项目供选择，切换项目时保留项目进度显示

## 流程执行界面

- [ ] 1. 待确认界面说人话，让人能看懂
- [ ] 2. 在工作的话要显示目前的工作状态，不能让用户错认我们正在进行的项目停止了
- [ ] 3. 工作中不允许点继续
- [ ] 4. 状态改成中文
- [ ] 5. 上面的进度？

## 质检升级

- [ ] 跨卷检查：答案泄露、知识点密度过高、公式指纹去重、图片指纹去重、数字替换题识别（依赖 image_refs/sha256/kpointIds 等 studio 暂无字段）
- [ ] 题型错误校验（对细目表逐题期望题型）：依赖逐题蓝图，studio 现无

## 规划表链路 / 成卷遗留（2026-07-02 审查）

> 由「跨卷查重」需求反查规划表链路得出。P1、P2 建议优先，且二者都绕着「三类卷号 vs 只落考点卷」。

- [x] P1. **专题训练卷 / 课程综合卷「成卷」路径已建**：新增 `planning.build_kaogang_papers`，`_gen_kaogang` 与 `gates.save_planning` 现把三类卷都落 papers（专题卷=每专题、综合卷=每课程 `comprehensive_per_course=3` 卷）。聚合卷 `meta.agg_texts` 自带其成员考点文本；`mapping._gen_mapping_kaogang` 逐卷解析并落库 `kpoint_id`+`meta.kpoint_ids`（聚合卷=成员并集去重），`pull.build_paper_plan`/`client.pull_for_plan` 支持多 `kpoint_ids` 拉题（题级 questionId 去重）。runner 逐卷循环随之覆盖三类卷。（未完成：无上传总表的 LLM 合成路径 `llm_gen` 仍只出考点卷骨架——待 API key，见 P4/P5；细目表 `mesh` 已过滤为仅按考点卷分组）
- [x] P2. **卷数口径已统一（通用#1 根因）**：`arrange_volume_numbers` 返回的 `total_volumes`（考点+专题+综合）现被 `_gen_kaogang` 接住作为卷数口径，三类卷全部落 papers → `total=len(papers)`/`_plan_total`/范围校验一致；`_gen_kaogang`/`save_planning` 已补 `ctx.selected_papers(total)` 按**全局卷号**筛选（不重编号，保留 1..N）。（回归：`backend/tests/test_kaogang_papers.py`、`test_kaogang_mapping.py`、`test_gen_kaogang_range.py`）
- [ ] P3. **两道人工确认闸门未串进 runner**（步骤文档 E1；关联通用#3）：`gates.py` / `Gates.vue` 已就绪，但 runner 仍「自动生成直接用」，缺「生成规划 → 人工确认闸门 → 继续」的 review 暂停点。
- [ ] P4. **无上传 10 列总表时考纲降级丢课程**：`_gen_kaogang` 找不到上传总表会回退 `_gen_generic`（不产 course/meta，跨卷分组键丢失）。→ LLM 生成/无总表路径补齐 course/meta 落库。
- [ ] P5. **规划表链路收尾**：LLM 实调（待 API key）+ 前端闸门页浏览器端到端联调 + `Q：规划表生成.md §8.3` 原始卷号在 `build_paper_plan` 的配置分区匹配（待实现）。
