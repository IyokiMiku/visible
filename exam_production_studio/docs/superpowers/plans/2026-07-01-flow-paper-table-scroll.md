# Flow Paper Table Scroll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the flow page paper status table from stretching the page by making it scroll inside an adaptive height area.

**Architecture:** Implement this entirely in `frontend/src/views/Flow.vue`. Use Vue refs plus a resize listener to compute a bounded `paperTableMaxHeight`, then pass it to Element Plus `el-table` via `:max-height` so the table body scrolls internally.

**Tech Stack:** Vue 3 Composition API, TypeScript, Element Plus `el-table`, Vite build validation.

---

## File Structure

- Modify: `exam_production_studio/frontend/src/views/Flow.vue`
  - Add `paperTableMaxHeight` state and resize handling in the existing `<script setup>` block.
  - Bind the existing paper table to `:max-height="paperTableMaxHeight"`.
- No new tests.
  - The frontend has no test runner configured for component unit tests.
  - Validation is `npm run build` and manual browser inspection.

## Task 1: Add Adaptive Paper Table Height

**Files:**
- Modify: `exam_production_studio/frontend/src/views/Flow.vue:1-241`

- [ ] **Step 1: Add adaptive height state and helper**

In `Flow.vue`, after `const logBox = ref<HTMLElement>()`, add:

```ts
const paperTableMaxHeight = ref(260)
```

After `scrollLog()` add:

```ts
function updatePaperTableHeight() {
  if (typeof window === 'undefined') return
  paperTableMaxHeight.value = Math.max(180, Math.min(360, window.innerHeight - 460))
}
```

- [ ] **Step 2: Wire resize lifecycle**

In the existing `onMounted(async () => { ... })`, before `await refresh()`, add:

```ts
  updatePaperTableHeight()
  window.addEventListener('resize', updatePaperTableHeight)
```

Replace the existing one-line unmount handler:

```ts
onUnmounted(() => disconnect && disconnect())
```

with:

```ts
onUnmounted(() => {
  window.removeEventListener('resize', updatePaperTableHeight)
  disconnect && disconnect()
})
```

- [ ] **Step 3: Bind table max height**

Replace the existing paper table opening tag:

```vue
<el-table :data="flow.papers" size="small" style="margin-top: 10px">
```

with:

```vue
<el-table :data="flow.papers" size="small" :max-height="paperTableMaxHeight" style="margin-top: 10px">
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd /c/Users/Administrator/Documents/新建文件夹/visible/exam_production_studio/frontend
npm run build
```

Expected: PASS. Existing Vite chunk-size warnings are acceptable.

- [ ] **Step 5: Clean generated build metadata if needed**

Run:

```bash
git -C /c/Users/Administrator/Documents/新建文件夹/visible restore -- exam_production_studio/frontend/tsconfig.tsbuildinfo 2>/dev/null || true
git -C /c/Users/Administrator/Documents/新建文件夹/visible status --short
```

Expected: only `exam_production_studio/frontend/src/views/Flow.vue` is modified for this task, aside from pre-existing allowed runtime logs.

- [ ] **Step 6: Commit only Flow.vue**

Run:

```bash
git -C /c/Users/Administrator/Documents/新建文件夹/visible add exam_production_studio/frontend/src/views/Flow.vue
git -C /c/Users/Administrator/Documents/新建文件夹/visible commit -m "feat: constrain flow paper table height"
```

Expected: commit contains only `Flow.vue`.

## Manual Verification

- Open `http://localhost:5173` and navigate to a project flow page.
- Confirm the right-side paper table keeps a bounded height.
- Confirm many paper rows scroll inside the table instead of stretching the whole page.
- Resize the browser height and confirm the table height adjusts between about 180px and 360px.

## Self-Review

- Spec coverage: The table gets an adaptive maximum height, scrolls internally through Element Plus, and does not change backend data or log layout.
- Placeholder scan: No placeholders or deferred implementation steps remain.
- Type consistency: `paperTableMaxHeight` is a `ref<number>` used directly by Element Plus `max-height`.
