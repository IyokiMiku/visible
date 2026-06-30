<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const items = ref<any[]>([])
const current = ref<any>(null)

const TYPE_TAG: Record<string, string> = {
  AI_MATCH: 'warning', AI_GENERATE: 'primary', RULE_CONFLICT: 'danger', QC_FAIL: 'danger',
}

async function load() {
  items.value = await api.reviews(id, 'pending')
  current.value = items.value[0] || null
}
async function confirm(item: any) {
  await api.confirm(id, item.id, { adopt: true })
  ElMessage.success('已确认')
  await load()
}
async function back(item: any) {
  await api.returnReview(id, item.id)
  ElMessage.success('已退回重算')
  await load()
}
onMounted(load)
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>待确认事项 <el-badge :value="items.length" :hidden="!items.length" /></span>
        <el-button @click="router.push(`/projects/${id}/flow`)">返回流程</el-button>
      </div>
    </template>
    <el-row :gutter="16" v-if="items.length">
      <el-col :span="10">
        <el-table :data="items" highlight-current-row @current-change="(r: any) => (current = r)">
          <el-table-column label="类型" width="130">
            <template #default="{ row }"><el-tag :type="TYPE_TAG[row.type]">{{ row.type }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="paper_no" label="卷号" width="80" />
          <el-table-column prop="node" label="节点" />
        </el-table>
      </el-col>
      <el-col :span="14" v-if="current">
        <el-descriptions title="确认详情" :column="1" border>
          <el-descriptions-item label="类型">{{ current.type }}</el-descriptions-item>
          <el-descriptions-item label="卷号">{{ current.paper_no ?? '全局' }}</el-descriptions-item>
          <el-descriptions-item label="信度">{{ current.confidence }}</el-descriptions-item>
          <el-descriptions-item label="依据/建议">
            <pre style="white-space: pre-wrap; margin: 0">{{ JSON.stringify(current.payload, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 12px">
          <el-button type="primary" @click="confirm(current)">确认并继续</el-button>
          <el-button @click="back(current)">退回重算</el-button>
        </div>
      </el-col>
    </el-row>
    <el-empty v-else description="无待确认事项" />
  </el-card>
</template>
