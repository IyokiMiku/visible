<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../services/api'

const route = useRoute()
const id = route.params.id as string
const groups = ref<Record<string, any[]>>({})

function fmtSize(n: number): string {
  return n > 1024 ? `${(n / 1024).toFixed(1)} KB` : `${n} B`
}
function download(path: string) {
  window.open(api.downloadUrl(id, path), '_blank')
}
function zip() {
  window.open(api.zipUrl(id), '_blank')
}
onMounted(async () => {
  groups.value = await api.artifacts(id)
})
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>输出归档</span>
        <el-button type="primary" @click="zip">打包下载 ZIP</el-button>
      </div>
    </template>
    <template v-for="(files, name) in groups" :key="name">
      <el-divider content-position="left">{{ name }}（{{ files.length }}）</el-divider>
      <el-table :data="files" size="small" empty-text="无">
        <el-table-column prop="name" label="文件名" min-width="320" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">{{ fmtSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="download(row.path)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>
