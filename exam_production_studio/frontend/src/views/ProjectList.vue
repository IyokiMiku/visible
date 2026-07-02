<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api, type Project } from '../services/api'
import { PROJECT_STATUS_LABEL, PROJECT_STATUS_TYPE } from '../constants/status'

const router = useRouter()
// _seq：加载顺序生成的稳定序号，用于「序号」列排序
type Row = Project & { _seq: number }
const projects = ref<Row[]>([])
const loading = ref(false)

const TYPE_LABEL: Record<string, string> = {
  yikeyilian: '一课一练',
  kaogang_100: '考纲百套卷',
  shuangxi: '考点双析卷',
}
// 筛选项：从当前项目数据动态生成，去重并过滤空值
const typeFilters = computed(() =>
  Array.from(new Set(projects.value.map(p => p.paper_type).filter(Boolean)))
    .map(v => ({ text: TYPE_LABEL[v] || v, value: v })),
)
const provinceFilters = computed(() =>
  Array.from(new Set(projects.value.map(p => p.province).filter(Boolean)))
    .map(v => ({ text: v, value: v })),
)
const statusFilters = computed(() =>
  Array.from(new Set(projects.value.map(p => p.status).filter(Boolean)))
    .map(v => ({ text: PROJECT_STATUS_LABEL[v] || v, value: v })),
)

function filterType(value: string, row: Row): boolean {
  return row.paper_type === value
}
function filterProvince(value: string, row: Row): boolean {
  return row.province === value
}
function filterStatus(value: string, row: Row): boolean {
  return row.status === value
}

// 后端 created_at 为 ISO 格式（如 2026-07-01T16:10:00），去掉 T 更易读
function formatTime(s?: string): string {
  if (!s) return '-'
  return s.replace('T', ' ')
}

// 按序号排序
function sortBySeq(a: Row, b: Row): number {
  return a._seq - b._seq
}

// 按创建时间排序：解析为时间戳比较，空值排在最后
function sortByCreatedAt(a: Project, b: Project): number {
  const ta = a.created_at ? new Date(a.created_at).getTime() : NaN
  const tb = b.created_at ? new Date(b.created_at).getTime() : NaN
  const va = Number.isNaN(ta) ? -Infinity : ta
  const vb = Number.isNaN(tb) ? -Infinity : tb
  return va - vb
}

async function load() {
  loading.value = true
  try {
    const list = await api.listProjects()
    projects.value = list.map((p, i) => ({ ...p, _seq: i + 1 }))
  } finally {
    loading.value = false
  }
}

async function remove(id: string) {
  await ElMessageBox.confirm('确认删除该项目及其产物记录？', '提示', { type: 'warning' })
  await api.deleteProject(id)
  await load()
}

async function openFolder(id: string) {
  try {
    const res = await api.openOutputFolder(id)
    ElMessage.success(`已打开：${res?.path || '输出目录'}`)
  } catch {
    /* 错误已由全局拦截器提示 */
  }
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
      <el-table-column
        prop="_seq"
        label="序号"
        width="90"
        sortable
        :sort-method="sortBySeq"
      />
      <el-table-column prop="name" label="项目名称" min-width="180">
        <template #default="{ row }">
          <span class="clamp-2" :title="row.name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column
        label="产品类型"
        width="130"
        :filters="typeFilters"
        :filter-method="filterType"
      >
        <template #default="{ row }">
          <span class="clamp-2" :title="TYPE_LABEL[row.paper_type] || row.paper_type">{{ TYPE_LABEL[row.paper_type] || row.paper_type }}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="province"
        label="省份"
        width="130"
        :filters="provinceFilters"
        :filter-method="filterProvince"
      />
      <el-table-column prop="course" label="课程" min-width="140">
        <template #default="{ row }">
          <span class="clamp-2" :title="row.course">{{ row.course }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="paper_range" label="卷号范围" width="100" />
      <el-table-column
        prop="created_at"
        label="创建时间"
        width="170"
        sortable
        :sort-method="sortByCreatedAt"
      >
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column
        label="状态"
        width="100"
        :filters="statusFilters"
        :filter-method="filterStatus"
      >
        <template #default="{ row }">
          <el-tag :type="PROJECT_STATUS_TYPE[row.status] || 'info'">{{ PROJECT_STATUS_LABEL[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <div class="op-cell">
            <el-button size="small" @click="router.push(`/projects/${row.id}/flow`)">流程</el-button>
            <el-button size="small" @click="router.push(`/projects/${row.id}/artifacts`)">产物</el-button>
            <el-button size="small" type="primary" plain @click="openFolder(row.id)">打开文件夹</el-button>
            <el-button size="small" type="danger" @click="remove(row.id)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.op-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.op-cell .el-button {
  margin-left: 0;
}
.clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
  white-space: normal;
  word-break: break-word;
}

/* 放大排序箭头，并用 flex+gap 固定两箭头间距，避免不同缩放显示器下箭头贴合 */
:deep(.caret-wrapper) {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 24px;
  height: auto;
}
:deep(.sort-caret) {
  position: static;
  margin: 0;
  border-width: 7px;
}
</style>
