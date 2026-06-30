<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../services/api'

const route = useRoute()
const id = route.params.id as string
const data = ref<any>({ papers: [], summary: {} })

onMounted(async () => {
  data.value = await api.quality(id)
})
</script>

<template>
  <el-card>
    <template #header>质量摘要</template>
    <el-row :gutter="16" v-if="data.summary && data.summary.papers">
      <el-col :span="4"><el-statistic title="平均评分" :value="data.summary.avg_score" /></el-col>
      <el-col :span="4"><el-statistic title="题库采用" :value="data.summary.adopted" /></el-col>
      <el-col :span="4"><el-statistic title="AI 补题" :value="data.summary.ai_filled" /></el-col>
      <el-col :span="4"><el-statistic title="人工确认" :value="data.summary.manual_confirmed" /></el-col>
      <el-col :span="4"><el-statistic title="知识点覆盖" :value="data.summary.coverage" /></el-col>
      <el-col :span="4"><el-statistic title="题量完整度" :value="data.summary.completeness" /></el-col>
    </el-row>
    <el-empty v-else description="尚无质检数据（请先执行流程）" />

    <el-divider />
    <el-table :data="data.papers" empty-text="暂无">
      <el-table-column prop="paper_no" label="卷号" width="80" />
      <el-table-column prop="score" label="评分" width="90" />
      <el-table-column prop="adopted" label="采用" width="80" />
      <el-table-column prop="ai_filled" label="AI补题" width="90" />
      <el-table-column prop="ai_risk" label="AI风险" width="90" />
      <el-table-column prop="suggestion" label="交付建议" />
    </el-table>
  </el-card>
</template>
