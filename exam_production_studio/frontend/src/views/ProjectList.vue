<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { api, type Project } from '../services/api'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)

const TYPE_LABEL: Record<string, string> = {
  yikeyilian: '一课一练',
  kaogang_100: '考纲百套卷',
  shuangxi: '考点双析卷',
}
const STATUS_TYPE: Record<string, string> = {
  draft: 'info', ready: 'info', running: 'warning', review: 'warning', done: 'success', failed: 'danger',
}

async function load() {
  loading.value = true
  try {
    projects.value = await api.listProjects()
  } finally {
    loading.value = false
  }
}

async function remove(id: string) {
  await ElMessageBox.confirm('确认删除该项目及其产物记录？', '提示', { type: 'warning' })
  await api.deleteProject(id)
  await load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>项目列表</span>
        <el-button type="primary" @click="router.push('/projects/new')">新建项目</el-button>
      </div>
    </template>
    <el-table :data="projects" v-loading="loading" empty-text="暂无项目，点击右上角新建">
      <el-table-column prop="name" label="项目名称" min-width="180" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">{{ TYPE_LABEL[row.paper_type] || row.paper_type }}</template>
      </el-table-column>
      <el-table-column prop="province" label="省份" width="130" />
      <el-table-column prop="course" label="课程" min-width="140" />
      <el-table-column prop="paper_range" label="卷号范围" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_TYPE[row.status] || 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="router.push(`/projects/${row.id}/flow`)">流程</el-button>
          <el-button size="small" @click="router.push(`/projects/${row.id}/artifacts`)">产物</el-button>
          <el-button size="small" type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
