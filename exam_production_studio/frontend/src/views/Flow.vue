<script setup lang="ts">
import { computed, onMounted, onUnmounted, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'
import { connectFlowWs } from '../services/ws'
import { refreshSettingsStatus } from '../services/settingsStatus'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const flow = ref<any>({ flow_nodes: [], status: '', current_node: '', progress: 0, papers: [], pending_reviews: 0 })
const logs = ref<any[]>([])
const logBox = ref<HTMLElement>()
let disconnect: (() => void) | null = null

const activeStep = computed(() => {
  const i = flow.value.flow_nodes.indexOf(flow.value.current_node)
  return i < 0 ? 0 : i
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
const rerunNode = ref('')
async function doRerun() {
  if (!rerunNode.value) return
  await api.rerun(id, rerunNode.value)
  ElMessage.success('已触发回退重跑')
  setTimeout(refresh, 500)
}

const STATUS_TYPE: Record<string, string> = {
  ready: 'info', running: 'warning', review: 'warning', done: 'success', failed: 'danger',
}

onMounted(async () => {
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
onUnmounted(() => disconnect && disconnect())
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>流程执行</span>
        <el-tag :type="STATUS_TYPE[flow.status] || 'info'">{{ flow.status }}</el-tag>
      </div>
    </template>

    <el-steps :active="activeStep" align-center finish-status="success" style="margin-bottom: 16px">
      <el-step v-for="n in flow.flow_nodes" :key="n" :title="n" />
    </el-steps>

    <el-row :gutter="16">
      <el-col :span="16">
        <div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
          <el-button type="primary" @click="start">开始</el-button>
          <el-button @click="pause">暂停</el-button>
          <el-button type="success" @click="resume">继续</el-button>
          <el-select v-model="rerunNode" placeholder="选择回退节点" style="width: 160px" size="default">
            <el-option v-for="n in flow.flow_nodes" :key="n" :label="n" :value="n" />
          </el-select>
          <el-button @click="doRerun">回退重跑</el-button>
          <el-badge :value="flow.pending_reviews" :hidden="!flow.pending_reviews">
            <el-button @click="router.push(`/projects/${id}/reviews`)">待确认</el-button>
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
          <el-descriptions-item label="当前节点">{{ flow.current_node || '-' }}</el-descriptions-item>
          <el-descriptions-item label="待确认">{{ flow.pending_reviews }}</el-descriptions-item>
          <el-descriptions-item label="卷数">{{ flow.papers.length }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="flow.papers" size="small" style="margin-top: 10px">
          <el-table-column prop="paper_no" label="卷号" width="70" />
          <el-table-column prop="status" label="状态" />
        </el-table>
        <el-button style="margin-top: 10px" @click="router.push(`/projects/${id}/quality`)">查看质量摘要</el-button>
        <el-button style="margin-top: 10px" @click="router.push(`/projects/${id}/artifacts`)">输出归档</el-button>
      </el-col>
    </el-row>
  </el-card>
</template>
