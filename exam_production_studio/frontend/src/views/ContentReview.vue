<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../services/api'
import { renderMath } from '../services/math'

const route = useRoute()
const id = route.params.id as string

const papers = ref<any[]>([])
const currentNo = ref<number | null>(null)
const detail = ref<any>(null)
const loadingList = ref(false)
const loadingDetail = ref(false)

// 单题编辑缓冲：同一时刻只编辑一题
const editing = ref<number | null>(null)
const buf = reactive<{ stem: string; options: string[]; answer: string; analysis: string }>({
  stem: '', options: [], answer: '', analysis: '',
})
const regenLoading = ref<number | null>(null)
const approving = ref(false)

const SEV_TAG: Record<string, string> = { 严重: 'danger', 警告: 'warning', 信息: 'info' }

const confirmedSet = computed(() => new Set<number>((detail.value?.review?.confirmed_nos) || []))
const questions = computed<any[]>(() =>
  [...(detail.value?.questions || [])].sort((a, b) => a.number - b.number),
)
const wholeIssues = computed<any[]>(() =>
  (detail.value?.qc?.issues || []).filter((i: any) => i.scope !== '单题'),
)
function issuesOf(num: number): any[] {
  return (detail.value?.qc?.issues || []).filter((i: any) => i.scope === '单题' && i.question_no === num)
}
const allConfirmed = computed(() =>
  questions.value.length > 0 && questions.value.every((q) => confirmedSet.value.has(q.number)),
)

async function loadList() {
  loadingList.value = true
  try {
    papers.value = await api.crPapers(id)
    if (currentNo.value == null && papers.value.length) selectPaper(papers.value[0].paper_no)
  } finally {
    loadingList.value = false
  }
}

async function loadDetail(no: number) {
  loadingDetail.value = true
  try {
    detail.value = await api.crPaper(id, no)
  } finally {
    loadingDetail.value = false
  }
}

function selectPaper(no: number) {
  currentNo.value = no
  editing.value = null
  loadDetail(no)
}

function startEdit(q: any) {
  editing.value = q.number
  buf.stem = q.stem || ''
  buf.options = [...(q.options || [])]
  buf.answer = q.answer || ''
  buf.analysis = q.analysis || ''
}
function cancelEdit() {
  editing.value = null
}
async function saveEdit(q: any) {
  await api.crEditQuestion(id, currentNo.value!, q.number, {
    stem: buf.stem, options: buf.options, answer: buf.answer, analysis: buf.analysis,
  })
  ElMessage.success(`第${q.number}题已保存（需重新确认）`)
  editing.value = null
  await loadDetail(currentNo.value!)
}

async function moveOption(q: any, i: number, dir: number) {
  const j = i + dir
  if (j < 0 || j >= q.options.length) return
  const order = q.options.map((_: any, k: number) => k)
  ;[order[i], order[j]] = [order[j], order[i]]
  await api.crReorderOptions(id, currentNo.value!, q.number, order)
  ElMessage.success('选项顺序已调整，答案已同步')
  await loadDetail(currentNo.value!)
}

async function regenerate(q: any) {
  try {
    await ElMessageBox.confirm(`确认让 AI 重新生成第${q.number}题？将覆盖当前题干/选项/答案/解析。`, '提示', { type: 'warning' })
  } catch {
    return
  }
  regenLoading.value = q.number
  try {
    await api.crRegenerate(id, currentNo.value!, q.number)
    ElMessage.success(`第${q.number}题已重生成（需重新确认）`)
    await loadDetail(currentNo.value!)
  } finally {
    regenLoading.value = null
  }
}

async function confirmQuestion(q: any) {
  await api.crConfirm(id, currentNo.value!, q.number)
  await loadDetail(currentNo.value!)
}

async function approve() {
  approving.value = true
  try {
    const r = await api.crApprove(id, currentNo.value!)
    ElMessage.success(r?.resumed ? '整卷已通过，流程已自动继续装配' : '整卷已通过（仍有其它卷待审）')
    await loadList()
    if (currentNo.value != null) await loadDetail(currentNo.value)
  } finally {
    approving.value = false
  }
}

function optionLetter(i: number): string {
  return String.fromCharCode(65 + i)
}

onMounted(loadList)
</script>

<template>
  <el-row :gutter="12">
    <!-- 左：待审卷列表 -->
    <el-col :span="6">
      <el-card v-loading="loadingList">
        <template #header><span>内容审阅 · 待审卷</span></template>
        <el-empty v-if="!papers.length" description="暂无需要审阅的卷（质检通过的卷已自动装配）" />
        <div
          v-for="p in papers"
          :key="p.paper_no"
          class="paper-item"
          :class="{ active: p.paper_no === currentNo }"
          @click="selectPaper(p.paper_no)"
        >
          <div style="display: flex; justify-content: space-between; align-items: center">
            <strong>第{{ p.paper_no }}卷</strong>
            <el-tag size="small" :type="p.status === '已通过' ? 'success' : 'warning'">{{ p.status || '待审' }}</el-tag>
          </div>
          <div style="color: #888; font-size: 12px; margin-top: 4px">{{ p.topic }}</div>
          <div style="font-size: 12px; margin-top: 4px">
            评分 {{ p.score ?? '-' }} · <span style="color: #f56c6c">严重 {{ p.severe }}</span>
            · <span style="color: #e6a23c">警告 {{ p.warning }}</span>
            · 已确认 {{ p.confirmed }}/{{ p.total }}
          </div>
        </div>
      </el-card>
    </el-col>

    <!-- 右：题目审阅 -->
    <el-col :span="18">
      <el-card v-loading="loadingDetail">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span v-if="detail">第{{ detail.paper_no }}卷 · {{ detail.meta?.topic || '' }}（{{ questions.length }} 题）</span>
            <span v-else>请选择左侧待审卷</span>
            <el-button
              v-if="detail"
              type="primary"
              :loading="approving"
              :disabled="!allConfirmed"
              @click="approve"
            >整卷通过（{{ confirmedSet.size }}/{{ questions.length }}）</el-button>
          </div>
        </template>

        <template v-if="detail">
          <!-- 整卷 / 跨卷问题（仅展示） -->
          <el-alert
            v-if="wholeIssues.length"
            type="warning"
            :closable="false"
            show-icon
            title="整卷 / 跨卷问题（仅提示，不阻拦通过）"
            style="margin-bottom: 12px"
          >
            <div v-for="(i, k) in wholeIssues" :key="k" style="font-size: 13px">
              <el-tag size="small" :type="SEV_TAG[i.severity] || 'info'" style="margin-right: 6px">{{ i.severity }}</el-tag>
              <strong>{{ i.type }}</strong>：{{ i.detail }}
            </div>
          </el-alert>

          <!-- 逐题卡片（题号升序） -->
          <div
            v-for="q in questions"
            :key="q.number"
            class="q-card"
            :class="{ confirmed: confirmedSet.has(q.number) }"
          >
            <div class="q-head">
              <span>
                <strong>第 {{ q.number }} 题</strong>
                <el-tag size="small" style="margin-left: 6px">{{ q.qtype }}</el-tag>
                <el-tag size="small" type="info" style="margin-left: 4px">{{ q.difficulty }}</el-tag>
                <el-tag v-if="q.source === 'ai'" size="small" type="warning" style="margin-left: 4px">AI</el-tag>
              </span>
              <el-tag v-if="confirmedSet.has(q.number)" type="success" size="small">已确认</el-tag>
              <el-tag v-else type="info" size="small">待确认</el-tag>
            </div>

            <!-- 该题质检问题 -->
            <div v-if="issuesOf(q.number).length" class="q-issues">
              <div v-for="(i, k) in issuesOf(q.number)" :key="k">
                <el-tag size="small" :type="SEV_TAG[i.severity] || 'info'" style="margin-right: 6px">{{ i.severity }}</el-tag>
                <strong>{{ i.type }}</strong>：{{ i.detail }}
              </div>
            </div>

            <!-- 查看态 -->
            <template v-if="editing !== q.number">
              <div class="field"><span class="label">题干</span><span v-html="renderMath(q.stem)"></span></div>
              <div v-for="im in q.stem_images || []" :key="im.src" class="imgs">
                <img :src="im.src" />
              </div>
              <div v-if="q.options && q.options.length" class="options">
                <div v-for="(opt, i) in q.options" :key="i" class="opt-row">
                  <span class="opt-label">{{ optionLetter(i) }}.</span>
                  <span v-html="renderMath(opt)"></span>
                  <span class="opt-actions">
                    <el-button size="small" text :disabled="i === 0" @click="moveOption(q, i, -1)">↑</el-button>
                    <el-button size="small" text :disabled="i === q.options.length - 1" @click="moveOption(q, i, 1)">↓</el-button>
                  </span>
                  <div v-for="im in (q.option_images && q.option_images[i]) || []" :key="im.src" class="imgs">
                    <img :src="im.src" />
                  </div>
                </div>
              </div>
              <div class="field"><span class="label">答案</span><span style="color: #f56c6c" v-html="renderMath(q.answer)"></span></div>
              <div class="field"><span class="label">解析</span><span v-html="renderMath(q.analysis)"></span></div>

              <div class="q-btns">
                <el-button size="small" @click="startEdit(q)">编辑</el-button>
                <el-button size="small" :loading="regenLoading === q.number" @click="regenerate(q)">AI 重生成</el-button>
                <el-button
                  size="small"
                  type="success"
                  :disabled="confirmedSet.has(q.number)"
                  @click="confirmQuestion(q)"
                >确认本题</el-button>
              </div>
            </template>

            <!-- 编辑态：源码编辑 + 实时公式预览 -->
            <template v-else>
              <div class="edit-grid">
                <div>
                  <div class="label">题干（可写 $...$ 公式源码）</div>
                  <el-input v-model="buf.stem" type="textarea" :rows="3" />
                  <div class="preview" v-html="renderMath(buf.stem)"></div>
                </div>
                <div v-if="buf.options.length">
                  <div class="label">选项</div>
                  <div v-for="(_, i) in buf.options" :key="i" style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px">
                    <span class="opt-label">{{ optionLetter(i) }}.</span>
                    <el-input v-model="buf.options[i]" size="small" />
                  </div>
                </div>
                <div>
                  <div class="label">答案</div>
                  <el-input v-model="buf.answer" />
                </div>
                <div>
                  <div class="label">解析</div>
                  <el-input v-model="buf.analysis" type="textarea" :rows="3" />
                  <div class="preview" v-html="renderMath(buf.analysis)"></div>
                </div>
              </div>
              <div class="q-btns">
                <el-button size="small" type="primary" @click="saveEdit(q)">保存</el-button>
                <el-button size="small" @click="cancelEdit">取消</el-button>
              </div>
            </template>
          </div>
        </template>
      </el-card>
    </el-col>
  </el-row>
</template>

<style scoped>
.paper-item {
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  cursor: pointer;
}
.paper-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.q-card {
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.q-card.confirmed {
  border-color: #67c23a;
  background: #f0f9eb;
}
.q-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.q-issues {
  background: #fdf6ec;
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 8px;
  font-size: 13px;
}
.field {
  margin: 4px 0;
  line-height: 1.6;
}
.label {
  display: inline-block;
  color: #909399;
  font-size: 12px;
  margin-right: 8px;
}
.options {
  margin: 6px 0;
}
.opt-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.opt-label {
  font-weight: 600;
  min-width: 20px;
}
.opt-actions {
  margin-left: auto;
}
.imgs img {
  max-width: 320px;
  max-height: 200px;
  margin: 4px 0;
  border: 1px solid #eee;
}
.q-btns {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
.edit-grid > div {
  margin-bottom: 10px;
}
.preview {
  margin-top: 4px;
  padding: 6px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 20px;
  font-size: 13px;
}
</style>
