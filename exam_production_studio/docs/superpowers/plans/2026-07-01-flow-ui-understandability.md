# Flow UI Understandability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the flow execution page understandable in Chinese, clearly show current work state, and prevent unsafe actions while a flow is running.

**Architecture:** Keep the change focused in `frontend/src/views/Flow.vue` by adding computed presentation state over the existing `flow` API response. No backend API, websocket, router, or data model changes are required.

**Tech Stack:** Vue 3 Composition API, TypeScript, Element Plus, Vite, existing `api` and `connectFlowWs` services.

---

## File Structure

- Modify: `exam_production_studio/frontend/src/views/Flow.vue`
  - Responsibility: render flow status, action buttons, logs, progress, papers, and navigation links.
  - Add local translation maps for flow statuses, nodes, and paper statuses.
  - Add computed state for status text, status type, human-readable guidance, and button disabled rules.
  - Update the template to use Chinese labels, a visible status alert, and safer button behavior.
- No new test files.
  - The frontend currently has no test runner or existing `*.test.ts` / `*.spec.ts` files.
  - Validation uses `npm run build`, which runs `vue-tsc -b && vite build`.

## Task 1: Add Flow Presentation State

**Files:**
- Modify: `exam_production_studio/frontend/src/views/Flow.vue:1-58`

- [ ] **Step 1: Add typed status helpers above the existing `activeStep` computed**

Insert this code after line 14, immediately after `let disconnect: (() => void) | null = null`:

```ts
type FlowStatus = 'ready' | 'running' | 'review' | 'paused' | 'blocked' | 'done' | 'failed'

const FLOW_STATUS_LABEL: Record<string, string> = {
  ready: '待开始',
  running: '执行中',
  review: '等待人工确认',
  paused: '已暂停',
  blocked: '已阻塞',
  done: '已完成',
  failed: '执行失败',
}

const FLOW_STATUS_TYPE: Record<string, string> = {
  ready: 'info',
  running: 'warning',
  review: 'warning',
  paused: 'info',
  blocked: 'warning',
  done: 'success',
  failed: 'danger',
}

const NODE_LABEL: Record<string, string> = {
  planning: '生成规划',
  mapping: '匹配考点',
  pull: '拉取试题',
  ai_generate: 'AI 补题',
  split: '拆分试卷',
  assemble: '组卷生成',
  qc: '质量检查',
  archive: '输出归档',
  review: '人工确认',
}

const PAPER_STATUS_LABEL: Record<string, string> = {
  ready: '待处理',
  running: '处理中',
  review: '待确认',
  done: '已完成',
  failed: '失败',
  skipped: '已跳过',
}

function labelFrom(map: Record<string, string>, value: unknown) {
  if (typeof value !== 'string' || !value) return '-'
  return map[value] || value
}
```

- [ ] **Step 2: Replace `activeStep` and `STATUS_TYPE` with computed presentation values**

Replace the existing `activeStep` computed and the `STATUS_TYPE` constant with this code:

```ts
const activeStep = computed(() => {
  const i = flow.value.flow_nodes.indexOf(flow.value.current_node)
  return i < 0 ? 0 : i
})

const flowStatus = computed(() => String(flow.value.status || 'ready') as FlowStatus)
const statusLabel = computed(() => labelFrom(FLOW_STATUS_LABEL, flowStatus.value))
const statusType = computed(() => FLOW_STATUS_TYPE[flowStatus.value] || 'info')
const currentNodeLabel = computed(() => labelFrom(NODE_LABEL, flow.value.current_node))
const isRunning = computed(() => flowStatus.value === 'running')
const canPause = computed(() => isRunning.value)
const canResume = computed(() => ['review', 'paused', 'blocked'].includes(flowStatus.value))
const canRerun = computed(() => !isRunning.value && !!rerunNode.value)
const pendingReviewText = computed(() => {
  const count = Number(flow.value.pending_reviews || 0)
  return count > 0 ? `处理待确认（${count}）` : '待确认'
})

const workStatusTitle = computed(() => {
  if (isRunning.value) return `正在执行：${currentNodeLabel.value}`
  if (flowStatus.value === 'review') return '流程已暂停，等待人工确认'
  if (flowStatus.value === 'blocked') return '流程已阻塞，需要先处理问题'
  if (flowStatus.value === 'paused') return '流程已暂停'
  if (flowStatus.value === 'done') return '流程已完成'
  if (flowStatus.value === 'failed') return '流程执行失败'
  return '流程尚未开始'
})

const workStatusDescription = computed(() => {
  const progress = Math.round(Number(flow.value.progress || 0))
  const pending = Number(flow.value.pending_reviews || 0)

  if (isRunning.value) {
    return `系统正在处理「${currentNodeLabel.value}」，当前进度约 ${progress}%。执行中不能点击继续或回退重跑，请等待状态更新。`
  }
  if (flowStatus.value === 'review') {
    return pending > 0
      ? `有 ${pending} 项内容需要人工确认。请先进入待确认事项处理，完成后再点击继续。`
      : '流程正在等待人工确认。确认完成后再点击继续。'
  }
  if (flowStatus.value === 'blocked') {
    return pending > 0
      ? `流程被待确认事项阻塞，共 ${pending} 项。处理完成后再点击继续。`
      : '流程被阻塞，请查看日志确认原因，处理后再继续。'
  }
  if (flowStatus.value === 'paused') {
    return '流程已暂停，可以点击继续恢复执行，也可以选择节点回退重跑。'
  }
  if (flowStatus.value === 'done') {
    return '全部流程已完成，可以查看质量摘要或输出归档。'
  }
  if (flowStatus.value === 'failed') {
    return '流程执行失败，请先查看日志中的错误信息，再决定是否回退重跑。'
  }
  return '点击开始后，系统会按步骤执行拉题、补题、组卷、质检和归档。'
})
```

- [ ] **Step 3: Run frontend type/build check to expose mistakes**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio/frontend
npm run build
```

Expected: this may fail until the template is updated in Task 2 because `STATUS_TYPE` will no longer exist if the template still references it. If it fails only with `STATUS_TYPE` missing, continue to Task 2.

## Task 2: Update Flow Template Copy and Button Rules

**Files:**
- Modify: `exam_production_studio/frontend/src/views/Flow.vue:75-126`

- [ ] **Step 1: Replace the header status tag**

Replace this template line:

```vue
<el-tag :type="STATUS_TYPE[flow.status] || 'info'">{{ flow.status }}</el-tag>
```

with:

```vue
<el-tag :type="statusType">{{ statusLabel }}</el-tag>
```

- [ ] **Step 2: Replace raw step titles with Chinese labels**

Replace this line:

```vue
<el-step v-for="n in flow.flow_nodes" :key="n" :title="n" />
```

with:

```vue
<el-step v-for="n in flow.flow_nodes" :key="n" :title="labelFrom(NODE_LABEL, n)" />
```

- [ ] **Step 3: Add the human-readable work status alert above the action buttons**

Insert this block immediately before the action button `<div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">`:

```vue
<el-alert
  :title="workStatusTitle"
  :description="workStatusDescription"
  :type="statusType === 'danger' ? 'error' : statusType === 'success' ? 'success' : statusType === 'warning' ? 'warning' : 'info'"
  show-icon
  :closable="false"
  style="margin-bottom: 12px"
/>
```

- [ ] **Step 4: Apply safe disabled rules to action buttons and select**

Replace the whole action button block with this code:

```vue
<div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
  <el-button type="primary" :disabled="isRunning" @click="start">开始</el-button>
  <el-button :disabled="!canPause" @click="pause">暂停</el-button>
  <el-button type="success" :disabled="!canResume" @click="resume">继续</el-button>
  <el-select v-model="rerunNode" placeholder="选择回退节点" style="width: 160px" size="default" :disabled="isRunning">
    <el-option v-for="n in flow.flow_nodes" :key="n" :label="labelFrom(NODE_LABEL, n)" :value="n" />
  </el-select>
  <el-button :disabled="!canRerun" @click="doRerun">回退重跑</el-button>
  <el-badge :value="flow.pending_reviews" :hidden="!flow.pending_reviews">
    <el-button :type="flow.pending_reviews ? 'warning' : 'default'" @click="router.push(`/projects/${id}/reviews`)">{{ pendingReviewText }}</el-button>
  </el-badge>
</div>
```

- [ ] **Step 5: Replace raw current node and paper statuses**

Replace this line:

```vue
<el-descriptions-item label="当前节点">{{ flow.current_node || '-' }}</el-descriptions-item>
```

with:

```vue
<el-descriptions-item label="当前节点">{{ currentNodeLabel }}</el-descriptions-item>
```

Replace this table column:

```vue
<el-table-column prop="status" label="状态" />
```

with:

```vue
<el-table-column label="状态">
  <template #default="scope">{{ labelFrom(PAPER_STATUS_LABEL, scope.row.status) }}</template>
</el-table-column>
```

- [ ] **Step 6: Run frontend build**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio/frontend
npm run build
```

Expected: PASS. The output should include `vue-tsc -b && vite build` and finish without TypeScript errors.

- [ ] **Step 7: Commit the UI template and state changes**

Run:

```bash
git -C /c/Users/Administrator/Documents/新建文件夹/visible status --short
git -C /c/Users/Administrator/Documents/新建文件夹/visible add exam_production_studio/frontend/src/views/Flow.vue
git -C /c/Users/Administrator/Documents/新建文件夹/visible commit -m "feat: clarify flow execution status"
```

Expected: a commit is created that modifies only `exam_production_studio/frontend/src/views/Flow.vue` for this implementation task.

## Task 3: Manual Verification Pass

**Files:**
- Verify: `exam_production_studio/frontend/src/views/Flow.vue`
- Verify: browser page `/projects/:id/flow`

- [ ] **Step 1: Start backend if it is not already running**

Run from the project root:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio
.venv/Scripts/python -m uvicorn main:app --app-dir backend --port 8000
```

Expected: the backend starts on `http://127.0.0.1:8000`. If `.venv` does not exist, run the repository `start.bat` from PowerShell instead because it creates the environment and installs dependencies.

- [ ] **Step 2: Start the frontend dev server**

Run in a second terminal:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio/frontend
npm run dev
```

Expected: Vite prints a local URL, normally `http://localhost:5173/`.

- [ ] **Step 3: Open a flow execution page and verify visible behavior**

Manual checks:

```text
1. Open an existing project flow page, or create a small project and navigate to its flow page.
2. Confirm the header status tag is Chinese, not raw `ready`, `running`, `review`, or `done`.
3. Confirm the alert explains the current state in a full Chinese sentence.
4. While status is running, confirm `继续`, `回退重跑`, and the node select are disabled.
5. When there are pending reviews, confirm the button reads `处理待确认（数量）`.
6. Confirm paper status values in the table display Chinese labels when known.
7. Confirm logs still append and auto-scroll.
```

Expected: all seven checks pass. Unknown backend status strings may remain visible as raw strings by design.

- [ ] **Step 4: Record final verification result**

Run:

```bash
git -C /c/Users/Administrator/Documents/新建文件夹/visible status --short
```

Expected: no uncommitted changes from verification, except generated runtime data such as `exam_production_studio/data/` if the app created local database/project files. Do not commit generated runtime data.

## Self-Review

- Spec coverage: Tasks 1 and 2 cover Chinese status mapping, human-readable current work state, disabled continue/rerun while running, clearer pending review copy, and fallback to raw unknown statuses. Task 3 covers build and manual verification.
- Placeholder scan: The plan contains no `TBD`, `TODO`, `implement later`, or vague unexpanded steps.
- Type consistency: Computed names used in the template are defined in Task 1: `statusType`, `statusLabel`, `currentNodeLabel`, `isRunning`, `canPause`, `canResume`, `canRerun`, `pendingReviewText`, `workStatusTitle`, and `workStatusDescription`.
