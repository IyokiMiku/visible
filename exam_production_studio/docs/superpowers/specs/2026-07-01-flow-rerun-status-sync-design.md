# 回退重跑状态同步设计

日期：2026-07-01

## 背景

流程执行页已有「回退重跑」按钮，但当前后端 `runner.rerun()` 只更新运行记录中的 `state.json`，随后重新启动流程。它没有立即重置当前 run 的 `current_node` 与 `progress`，也没有写入明显的回退日志。因此用户点击回退后，页面顶部进度条和右侧任务概况可能短时间保留旧状态，日志区也缺少本次回退的视觉分隔。

## 目标

点击「回退重跑」后，页面应立即反映回退范围：进度条回到对应区间，任务概况显示回退节点，日志区出现一条明显分割线，后续执行日志从分割线后继续追加。

## 非目标

- 不增加按单卷回退的前端选择能力。
- 不改变现有 `/flow/rerun` API 请求格式。
- 不重写流程执行状态机。
- 不清理或重生成历史产物文件。

## 方案

在后端 `backend/engine/runner.py` 中实现回退状态同步：

1. 增加「节点 key → 中文显示名」和「节点 key → 回退进度」映射。
2. `rerun(project_id, node, paper_no=None)` 解析出 `node_key` 后，先按现有逻辑更新 `state.json`。
3. 获取或创建当前 run，并立即更新：
   - `status='running'`
   - `current_node=<回退节点中文名>`
   - `progress=<映射进度>`
4. 写入一条普通日志作为分割线：
   - `────────── 回退重跑：从「xxx」重新开始 ──────────`
5. 发布一次 `progress` 事件，让前端 websocket 触发刷新。
6. 最后调用 `start(project_id)` 继续执行现有流程。

## 进度映射

- `load` / `kpoint`：0
- `planning`：20
- `mapping`：28
- `mesh`：36
- `naming`：44
- `pull` / `split` / `assemble` / `qc`：60
- 未知节点：0，并保留原始节点名作为显示名

## 验证

- 增加后端单元测试，直接调用 `runner.rerun()`，用 monkeypatch/mock 验证：
  - run 被更新为对应节点和进度
  - 写入了回退分割线日志
  - 发布了 progress 事件
  - 最后调用了 `start(project_id)`
- 运行新增测试。
- 如可用，运行前端构建确认现有流程页未受影响。
