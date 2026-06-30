<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const resources = ref<any[]>([])
const uploadUrl = api.uploadResourceUrl(id)

const KINDS = ['考纲', '教材', '真题', '模板', '规划表']

async function load() {
  resources.value = await api.listResources(id)
}
function onSuccess() {
  ElMessage.success('上传成功')
  load()
}
onMounted(load)
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>资源导入</span>
        <el-button type="primary" @click="router.push(`/projects/${id}/flow`)">进入流程执行</el-button>
      </div>
    </template>

    <div style="display: flex; gap: 16px; flex-wrap: wrap">
      <el-card v-for="k in KINDS" :key="k" style="width: 220px" shadow="never">
        <div style="margin-bottom: 8px"><strong>{{ k }}</strong></div>
        <el-upload
          :action="uploadUrl"
          :data="{ kind: k }"
          name="file"
          :on-success="onSuccess"
          :show-file-list="false"
        >
          <el-button size="small">选择文件上传</el-button>
        </el-upload>
      </el-card>
    </div>

    <el-divider />
    <el-table :data="resources" empty-text="尚未导入资源（可直接进入流程，使用本地合成/默认模板）">
      <el-table-column prop="kind" label="类型" width="100" />
      <el-table-column prop="filename" label="文件名" min-width="240" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }"><el-tag type="success">{{ row.status }}</el-tag></template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
