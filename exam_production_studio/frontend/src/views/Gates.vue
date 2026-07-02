<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const id = route.params.id as string

const activeTab = ref('toc')
const loading = ref(false)
const saving = ref(false)
const paperType = ref('')

// ===== 闸门1：结构化教材目录 =====
interface TocNode { level: number; title: string; page: number | null }
interface Toc { textbook: string; source_pdf: string; pdf_kind: string; nodes: TocNode[] }
const tocs = ref<Toc[]>([])
const activeToc = ref(0)

async function loadToc() {
  loading.value = true
  try {
    const res: any = await api.gateGetToc(id)
    tocs.value = (res.tocs || []).map((t: any) => ({ ...t, nodes: t.nodes || [] }))
    activeToc.value = 0
  } finally {
    loading.value = false
  }
}
function addTocNode() {
  const t = tocs.value[activeToc.value]
  if (t) t.nodes.push({ level: 2, title: '', page: null })
}
function removeTocNode(i: number) {
  tocs.value[activeToc.value]?.nodes.splice(i, 1)
}
async function saveToc() {
  const t = tocs.value[activeToc.value]
  if (!t) return
  saving.value = true
  try {
    await api.gateSaveToc(id, t)
    ElMessage.success('目录已保存（闸门1 确认）')
  } finally {
    saving.value = false
  }
}

// ===== 闸门2：规划表行 =====
interface PlanRow {
  paper_no?: number
  topic?: string
  point_name?: string
  level?: string
  unit_name?: string
  chapter_name?: string
  course?: string
  theme?: string
}
const rows = ref<PlanRow[]>([])
const LEVELS = ['极重要', '重要', '标准']

async function loadPlanning() {
  loading.value = true
  try {
    const res: any = await api.gateGetPlanning(id)
    paperType.value = res.paper_type || ''
    rows.value = res.rows || []
  } finally {
    loading.value = false
  }
}
function addRow() {
  if (paperType.value === 'kaogang_100')
    rows.value.push({ course: '', theme: '', topic: '', point_name: '' })
  else if (paperType.value === 'shuangxi')
    rows.value.push({ course: '', topic: '', point_name: '', level: '标准' })
  else rows.value.push({ course: '', unit_name: '', chapter_name: '', topic: '', point_name: '', level: '标准' })
}
function removeRow(i: number) {
  rows.value.splice(i, 1)
}
async function savePlanning(force = false) {
  saving.value = true
  try {
    const payload = rows.value.map((r) => {
      if (paperType.value === 'kaogang_100')
        return { course: r.course, theme: r.theme, point_name: r.topic, knowledge: r.point_name }
      if (paperType.value === 'shuangxi')
        return { course: r.course, topic: r.topic, point_name: r.point_name, level: r.level }
      return {
        course: r.course, unit_name: r.unit_name, chapter_name: r.chapter_name,
        topic: r.topic, point_name: r.point_name, level: r.level,
      }
    })
    const res: any = await api.gateSavePlanning(id, payload, force)
    if (!res.saved) {
      const issues = (res.validation?.issues || [])
        .filter((x: any) => x.severity === '严重')
        .map((x: any) => `· ${x.detail}`)
        .join('\n')
      await ElMessageBox.confirm(
        `校验发现严重问题，未放行：\n${issues || '（见校验详情）'}\n\n是否人工确认强制放行？`,
        '闸门2 校验未通过',
        { confirmButtonText: '强制放行', cancelButtonText: '返回修改', type: 'warning' },
      )
      return savePlanning(true)
    }
    ElMessage.success('规划表已保存并重渲染（闸门2 确认）')
  } finally {
    saving.value = false
  }
}

function reload() {
  activeTab.value === 'toc' ? loadToc() : loadPlanning()
}
onMounted(() => {
  loadToc()
  loadPlanning()
})
</script>

<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>人工确认闸门（简略展示 · 可编辑 · 可增条目）</span>
        <el-button size="small" :loading="loading" @click="reload">刷新</el-button>
      </div>
    </template>

    <el-tabs v-model="activeTab">
      <!-- 闸门1：读取结果（结构化目录）-->
      <el-tab-pane label="闸门1 · 读取结果（教材目录）" name="toc">
        <div v-loading="loading">
          <el-alert
            type="info" :closable="false" show-icon
            title="校对 OCR/文本层抽取的教材目录层级；可修改层级/标题，可新增条目。确认后写回 toc_structured.json。"
          />
          <div v-if="!tocs.length" class="muted pad">暂无结构化目录（先在流程里跑“解析目录”）。</div>
          <template v-else>
            <el-radio-group v-model="activeToc" class="pad">
              <el-radio-button v-for="(t, i) in tocs" :key="i" :value="i">
                {{ t.textbook }}（{{ t.pdf_kind }}）
              </el-radio-button>
            </el-radio-group>
            <el-table :data="tocs[activeToc]?.nodes || []" size="small" border max-height="52vh">
              <el-table-column label="层级" width="120">
                <template #default="{ row }">
                  <el-select v-model="row.level" size="small">
                    <el-option :value="1" label="一级(单元/章)" />
                    <el-option :value="2" label="二级(章/节)" />
                    <el-option :value="3" label="三级(条目)" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="标题">
                <template #default="{ row }">
                  <el-input v-model="row.title" size="small" placeholder="目录标题" />
                </template>
              </el-table-column>
              <el-table-column label="页码" width="90">
                <template #default="{ row }">
                  <el-input v-model.number="row.page" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ $index }">
                  <el-button size="small" type="danger" text @click="removeTocNode($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="actions">
              <el-button size="small" @click="addTocNode">+ 新增条目</el-button>
              <el-button size="small" type="primary" :loading="saving" @click="saveToc">确认并保存</el-button>
            </div>
          </template>
        </div>
      </el-tab-pane>

      <!-- 闸门2：生成结果（规划表行）-->
      <el-tab-pane label="闸门2 · 生成结果（规划表）" name="plan">
        <div v-loading="loading">
          <el-alert
            type="info" :closable="false" show-icon
            :title="`校对生成的规划表行；可修改/新增。保存时代码校验（硬拦截），不达标可人工强制放行。当前类型：${paperType || '未知'}`"
          />
          <!-- 一课一练 扁平列式 -->
          <el-table v-if="paperType === 'yikeyilian'" :data="rows" size="small" border max-height="52vh">
            <el-table-column label="#" type="index" width="48" />
            <el-table-column label="课程" width="120">
              <template #default="{ row }"><el-input v-model="row.course" size="small" /></template>
            </el-table-column>
            <el-table-column label="一级(单元)">
              <template #default="{ row }"><el-input v-model="row.unit_name" size="small" /></template>
            </el-table-column>
            <el-table-column label="二级(章)">
              <template #default="{ row }"><el-input v-model="row.chapter_name" size="small" /></template>
            </el-table-column>
            <el-table-column label="试卷主题(C)">
              <template #default="{ row }"><el-input v-model="row.topic" size="small" /></template>
            </el-table-column>
            <el-table-column label="考纲知识点(B)">
              <template #default="{ row }"><el-input v-model="row.point_name" size="small" /></template>
            </el-table-column>
            <el-table-column label="级别" width="110">
              <template #default="{ row }">
                <el-select v-model="row.level" size="small">
                  <el-option v-for="l in LEVELS" :key="l" :value="l" :label="l" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button size="small" type="danger" text @click="removeRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 考点双析卷 扁平（一行=一练，装配拆教师/学生）-->
          <el-table v-else-if="paperType === 'shuangxi'" :data="rows" size="small" border max-height="52vh">
            <el-table-column label="练号" type="index" width="60" />
            <el-table-column label="课程" width="140">
              <template #default="{ row }"><el-input v-model="row.course" size="small" /></template>
            </el-table-column>
            <el-table-column label="试卷主题">
              <template #default="{ row }"><el-input v-model="row.topic" size="small" /></template>
            </el-table-column>
            <el-table-column label="考纲知识点">
              <template #default="{ row }"><el-input v-model="row.point_name" size="small" type="textarea" :rows="1" /></template>
            </el-table-column>
            <el-table-column label="级别" width="110">
              <template #default="{ row }">
                <el-select v-model="row.level" size="small">
                  <el-option v-for="l in LEVELS" :key="l" :value="l" :label="l" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button size="small" type="danger" text @click="removeRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 考纲百套卷 10 列（简略）-->
          <el-table v-else :data="rows" size="small" border max-height="52vh">
            <el-table-column label="#" type="index" width="48" />
            <el-table-column label="课程(A)">
              <template #default="{ row }"><el-input v-model="row.course" size="small" /></template>
            </el-table-column>
            <el-table-column label="专题(B)">
              <template #default="{ row }"><el-input v-model="row.theme" size="small" /></template>
            </el-table-column>
            <el-table-column label="考点(C)">
              <template #default="{ row }"><el-input v-model="row.topic" size="small" /></template>
            </el-table-column>
            <el-table-column label="知识点(D)">
              <template #default="{ row }"><el-input v-model="row.point_name" size="small" type="textarea" :rows="1" /></template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button size="small" type="danger" text @click="removeRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="actions">
            <el-button size="small" @click="addRow">+ 新增行</el-button>
            <el-button size="small" @click="loadPlanning">回退（放弃修改）</el-button>
            <el-button size="small" type="primary" :loading="saving" @click="savePlanning(false)">
              确认并保存（校验+重渲染）
            </el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pad {
  margin: 10px 0;
}
.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.muted {
  color: var(--el-text-color-secondary);
}
</style>
