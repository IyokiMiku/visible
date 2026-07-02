<script setup lang="ts">
import { computed, onMounted, onUnmounted, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'
import { connectFlowWs } from '../services/ws'
import { refreshSettingsStatus } from '../services/settingsStatus'
import { PROJECT_STATUS_LABEL, PROJECT_STATUS_TYPE } from '../constants/status'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const flow = ref<any>({ flow_nodes: [], status: '', current_node: '', progress: 0, papers: [], pending_reviews: 0 })
const logs = ref<any[]>([])
const logBox = ref<HTMLElement>()
const paperTableMaxHeight = ref(260)
let disconnect: (() => void) | null = null

type FlowStatus = 'ready' | 'running' | 'review' | 'paused' | 'blocked' | 'done' | 'failed'

const PAPER_STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  ready: '待处理',
  running: '处理中',
  pulled: '已拉题',
  qc_passed: '质检通过',
  pending_review: '待人工确认',
  review: '待确认',
  done: '已完成',
  failed: '失败',
  skipped: '已跳过',
}

function labelFrom(map: Record<string, string>, value: unknown) {
  if (typeof value !== 'string' || !value) return '-'
  return map[value] || value
}

const rerunNode = ref('')

const activeStep = computed(() => {
  const i = flow.value.flow_nodes.indexOf(flow.value.current_node)
  return i < 0 ? 0 : i
})

const flowStatus = computed(() => String(flow.value.status || 'ready') as FlowStatus)
const statusLabel = computed(() => labelFrom(PROJECT_STATUS_LABEL, flowStatus.value))
const statusType = computed(() => PROJECT_STATUS_TYPE[flowStatus.value] || 'info')
const alertType = computed(() =>
  statusType.value === 'danger'
    ? 'error'
    : statusType.value === 'warning'
      ? 'warning'
      : statusType.value === 'success'
        ? 'success'
        : 'info',
)
const currentNodeLabel = computed(() => flow.value.current_node || '-')
// 回退可选节点：排除「内容审阅」——它是质检不过时的人工暂停点，不是可独立重跑的生产阶段
const rerunableNodes = computed(() =>
  (flow.value.flow_nodes as string[]).filter(n => n !== '内容审阅'),
)
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

async function refresh() {
  flow.value = await api.getFlow(id)
}
async function loadLogs() {
  logs.value = await api.logs(id)
  scrollLog()
}
function scrollLog() {
  nextTick(() => {
    if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
  })
}
function updatePaperTableHeight() {
  if (typeof window === 'undefined') return
  paperTableMaxHeight.value = Math.max(180, Math.min(360, window.innerHeight - 460))
}

async function start() {
  await api.start(id)
  ElMessage.success('已开始')
  setTimeout(refresh, 500)
}
async function pause() {
  await api.pause(id)
  refresh()
}
async function resume() {
  await api.resume(id)
  ElMessage.success('已继续')
  setTimeout(refresh, 500)
}
async function doRerun() {
  if (!rerunNode.value) return
  await api.rerun(id, rerunNode.value)
  ElMessage.success('已触发回退重跑')
  setTimeout(refresh, 500)
}

onMounted(async () => {
  updatePaperTableHeight()
  window.addEventListener('resize', updatePaperTableHeight)
  await refresh()
  await loadLogs()
  disconnect = connectFlowWs(id, (ev) => {
    if (ev.event === 'log' || ev.message) {
      logs.value.push({ node: ev.node, level: ev.level, message: ev.message, created_at: ev.time })
      scrollLog()
    }
    if (['progress', 'review', 'paused', 'done', 'error', 'blocked'].includes(ev.event)) refresh()
    // 运行失败或完成后，刷新全局设置状态（用于精准点亮/熄灭「全局设置」红点）
    if (ev.event === 'error' || ev.event === 'done') refreshSettingsStatus()
    if (ev.event === 'review') ElMessage.warning('命中待确认事项，请前往「待确认事项」处理')
  })
})
onUnmounted(() => {
  window.removeEventListener('resize', updatePaperTableHeight)
  disconnect && disconnect()
})
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>流程执行</span>
        <el-tag :type="statusType">{{ statusLabel }}</el-tag>
      </div>
    </template>

    <el-steps :active="activeStep" align-center finish-status="success" style="margin-bottom: 16px">
      <el-step v-for="n in flow.flow_nodes" :key="n" :title="n" />
    </el-steps>

    <el-row :gutter="16">
      <el-col :span="16">
        <el-alert
          :title="workStatusTitle"
          :description="workStatusDescription"
          :type="alertType"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <el-button type="primary" :disabled="isRunning" @click="start">开始</el-button>
          <el-button :disabled="!canPause" @click="pause">暂停</el-button>
          <el-button type="success" :disabled="!canResume" @click="resume">继续</el-button>
          <el-select v-model="rerunNode" placeholder="选择回退节点" style="width: 160px" size="default" :disabled="isRunning">
            <el-option v-for="n in rerunableNodes" :key="n" :label="n" :value="n" />
          </el-select>
          <el-button :disabled="!canRerun" @click="doRerun">回退重跑</el-button>
          <el-badge :value="flow.pending_reviews" :hidden="!flow.pending_reviews">
            <el-button @click="router.push(`/projects/${id}/reviews`)">{{ pendingReviewText }}</el-button>
          </el-badge>
        </div>
        <div
          ref="logBox"
          style="height: 360px; overflow: auto; background: #0d1117; color: #c9d1d9; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px"
        >
          <div v-for="(l, i) in logs" :key="i" :style="{ color: l.level === 'error' ? '#ff7b72' : l.level === 'warn' ? '#e3b341' : '#c9d1d9' }">
            [{{ l.node || '-' }}] {{ l.message }}
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <el-descriptions title="任务概况" :column="1" border>
          <el-descriptions-item label="进度">
            <el-progress :percentage="Math.round(flow.progress)" />
          </el-descriptions-item>
          <el-descriptions-item label="当前节点">{{ currentNodeLabel }}</el-descriptions-item>
          <el-descriptions-item label="待确认">{{ flow.pending_reviews }}</el-descriptions-item>
          <el-descriptions-item label="卷数">{{ flow.papers.length }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="flow.papers" size="small" style="margin-top: 10px" :max-height="paperTableMaxHeight">
          <el-table-column prop="paper_no" label="卷号" width="70" />
          <el-table-column label="状态">
            <template #default="scope">{{ labelFrom(PAPER_STATUS_LABEL, scope.row.status) }}</template>
          </el-table-column>
        </el-table>
        <el-button style="margin-top: 10px" @click="router.push(`/projects/${id}/quality`)">查看质量摘要</el-button>
        <el-button style="margin-top: 10px" @click="router.push(`/projects/${id}/artifacts`)">输出归档</el-button>
      </el-col>
    </el-row>
  </el-card>
</template>
