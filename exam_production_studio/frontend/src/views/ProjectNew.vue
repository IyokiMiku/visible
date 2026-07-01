<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { api } from '../services/api'

const route = useRoute()
const router = useRouter()

const TYPES = [
  { value: 'yikeyilian', label: '一课一练', desc: '教材目录基础 · 逐练小卷 · ×1' },
  { value: 'kaogang_100', label: '考纲百套卷', desc: '考纲基础 · 含细目表 · ×1' },
  { value: 'shuangxi', label: '考点双析卷', desc: '考纲基础 · 拉题×2 · 奇偶分卷' },
]

// 题型下拉：按 卷类/考类/课程 从后端 题型定义 动态加载（标准名，别名如“单选题”已统一为“单项选择题”）。
// 接口不可用或未命中时，回退到这份全局标准名列表，保证下拉不为空。
const FALLBACK_QUESTION_TYPES = [
  '单项选择题',
  '多项选择题',
  '判断题',
  '填空题',
  '简答题',
  '综合应用题',
  '计算题',
  '作图题',
  '识图题',
  '简答作图题',
]
const questionTypes = ref<string[]>([...FALLBACK_QUESTION_TYPES])
// 用户自定义题型（学科网未收录、但实际需要的题型，如“名词解释题”）。
// 后端按“考类/课程”绑定存储；这里保留会话副本，供下拉即时显示与合法性判断。
const customTypes = ref<string[]>([])
// 当前 考类/课程 对应的题型库条目 id（下拉快速加/校验时用于定位绑定分组）。
const currentEntryId = ref<string>('__global__')
// 下拉“自定义题型…”的哨兵值，选中后弹出输入框，不会作为真实题型写入。
const CUSTOM_OPTION = '__custom__'

// 自定义题型统一以“题”结尾（如 名词解释 → 名词解释题），空值返回空串。
function ensureQuestionSuffix(name: string): string {
  const n = (name || '').trim()
  if (!n) return ''
  return n.endsWith('题') ? n : n + '题'
}

const DEFAULT_VOLUME: Record<string, any[]> = {
  yikeyilian: [
    { type: '单项选择题', count: 5, score_per: 2 },
    { type: '填空题', count: 3, score_per: 2 },
    { type: '综合应用题', count: 2, score_per: 5 },
  ],
  kaogang_100: [
    { type: '单项选择题', count: 20, score_per: 2 },
    { type: '填空题', count: 10, score_per: 2 },
    { type: '判断题', count: 10, score_per: 1 },
    { type: '简答题', count: 4, score_per: 5 },
    { type: '综合应用题', count: 1, score_per: 10 },
  ],
  shuangxi: [
    { type: '单项选择题', count: 25, score_per: 2 },
    { type: '填空题', count: 15, score_per: 2 },
    { type: '判断题', count: 20, score_per: 1 },
  ],
}

const form = reactive<any>({
  paper_type: (route.query.type as string) || 'yikeyilian',
  name: '',
  province: '',
  exam_type_name: '高职分类考试',
  exam_type_name_other: '',
  exam_category: '',
  course: '',
  textbook: '',
  edition: '',
  exam_minutes: 60,
  plan_source: 'ocr',
  output_versions: ['原卷版', '解析版'],
  difficulty: { easy: 80, medium: 10, hard: 10 },
  narrow_point: { enabled: true, merge_threshold: 80 },
  ai: { match: true, summary: true, fill: true, match_threshold: 0.85, max_fix_rounds: 2 },
  volume: JSON.parse(JSON.stringify(DEFAULT_VOLUME['yikeyilian'])),
})

// 卷号范围：多区间 [{start,end}]，各自正整数、前<后、互不重叠，最终取并集。
const ranges = ref<{ start: number; end: number }[]>([{ start: 1, end: 1 }])
// 已生成规划表得到的总卷量（0 = 尚未生成），卷号范围不得超过它。
const planTotal = ref(0)
// 三步向导 + 草稿项目 id（第一步「下一步」时创建草稿，第三步保存置为 ready）。
const currentStep = ref(0)
const projectId = ref<string>('')

// 创建项目表单草稿：跳到全局设置再回来时，防止已填内容/所处步骤丢失。
// 用 sessionStorage：同一标签页内跳转/回退保留，关闭标签页自动清空（临时草稿语义）。
const DRAFT_KEY = 'projectNewDraft'
let restoring = false

function saveDraft() {
  try {
    sessionStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        form,
        step: currentStep.value,
        projectId: projectId.value,
        ranges: ranges.value,
        planTotal: planTotal.value,
      }),
    )
  } catch {
    /* 隐私模式/容量异常时忽略，不影响填写 */
  }
}

function loadDraft(): boolean {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (!raw) return false
    const saved = JSON.parse(raw)
    // 兼容旧格式（直接存 form）与新格式（{ form, step, ... }）
    const savedForm = saved && saved.form ? saved.form : saved
    restoring = true
    Object.assign(form, savedForm)
    currentStep.value = typeof saved?.step === 'number' ? saved.step : 0
    projectId.value = saved?.projectId || ''
    if (Array.isArray(saved?.ranges) && saved.ranges.length) ranges.value = saved.ranges
    planTotal.value = typeof saved?.planTotal === 'number' ? saved.planTotal : 0
    // paper_type 的 watcher 会在下个 tick 触发，restoring 标志避免其覆盖恢复的 volume
    nextTick(() => {
      restoring = false
    })
    return true
  } catch {
    return false
  }
}

function clearDraft() {
  sessionStorage.removeItem(DRAFT_KEY)
}

watch(
  () => form.paper_type,
  (t) => {
    loadFullScore()
    if (restoring) return
    form.volume = JSON.parse(JSON.stringify(DEFAULT_VOLUME[t] || DEFAULT_VOLUME['yikeyilian']))
  },
)

// 深度监听表单/步骤/范围，任何改动即写入草稿
watch(form, saveDraft, { deep: true })
watch(currentStep, saveDraft)
watch(ranges, saveDraft, { deep: true })
watch(planTotal, saveDraft)

async function loadQuestionTypes() {
  try {
    const res: any = await api.getQuestionTypes(form.paper_type, form.course, form.exam_category)
    const list: string[] = (res && res.question_types) || []
    questionTypes.value = list.length ? list : [...FALLBACK_QUESTION_TYPES]
    customTypes.value = (res && res.custom_types) || []
    currentEntryId.value = (res && res.matched_id) || '__global__'
  } catch {
    questionTypes.value = [...FALLBACK_QUESTION_TYPES]
    customTypes.value = []
    currentEntryId.value = '__global__'
  }
}

let qtTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => [form.paper_type, form.course, form.exam_category],
  () => {
    if (qtTimer) clearTimeout(qtTimer)
    qtTimer = setTimeout(loadQuestionTypes, 400)
  },
)

// 下拉可选题型 = 后端题型 + 自定义题型（去重，自定义在末尾）
const allTypes = computed(() => {
  const seen = new Set<string>()
  const merged: string[] = []
  for (const t of [...questionTypes.value, ...customTypes.value]) {
    if (t && !seen.has(t)) {
      seen.add(t)
      merged.push(t)
    }
  }
  return merged
})
const validTypeSet = computed(() => new Set(allTypes.value))

async function onTypeChange(row: any, val: string) {
  if (val !== CUSTOM_OPTION) return
  row.type = ''
  try {
    const { value } = await ElMessageBox.prompt(
      '请输入自定义题型名称（会自动以“题”结尾，如 名词解释 → 名词解释题）',
      '自定义题型',
      { confirmButtonText: '确定', cancelButtonText: '取消', inputPattern: /\S/, inputErrorMessage: '题型名称不能为空' },
    )
    const name = ensureQuestionSuffix(value || '')
    if (!name) return
    // 持久化到当前 考类/课程 绑定分组（覆盖式保存全量列表）
    if (!customTypes.value.includes(name)) {
      const next = [...customTypes.value, name]
      try {
        await api.saveCustomTypes(form.paper_type, currentEntryId.value, next)
      } catch {
        /* 保存失败已由拦截器提示，仍允许本次会话临时使用 */
      }
      customTypes.value = next
    }
    if (!questionTypes.value.includes(name)) questionTypes.value.push(name)
    row.type = name
  } catch {
    /* 用户取消，保持未选择 */
  }
}
// 行的题型已选、但不在当前选项集合内 → 失效（切换卷类/考类/课程后可能出现）
function isRowInvalid(row: any): boolean {
  return !!row.type && !validTypeSet.value.has(row.type)
}
// 题型选项变化后，提示哪些已填行的题型失效（不自动删除，避免丢失已填题量/分值）
watch(questionTypes, () => {
  const bad = [...new Set(form.volume.filter((r: any) => isRowInvalid(r)).map((r: any) => r.type))]
  if (bad.length) {
    ElMessage.warning(`当前考类不支持以下题型，已高亮，请重新选择：${bad.join('、')}`)
  }
})

const diffSum = computed(() => form.difficulty.easy + form.difficulty.medium + form.difficulty.hard)

// 考试名称：选“其他名称”时取自填框
function resolvedExamTypeName(): string {
  return form.exam_type_name === '__other__' ? (form.exam_type_name_other || '').trim() : form.exam_type_name
}

// 该产品系列满分：一课一练不标注分数（scoreEnabled=false），其余默认 100，可在产品系列设置里改。
const scoreEnabled = ref(true)
const fullScore = ref(100)
async function loadFullScore() {
  try {
    const d: any = await api.getPaperType(form.paper_type)
    scoreEnabled.value = d.score_enabled !== false
    fullScore.value = typeof d.full_score === 'number' ? d.full_score : 100
  } catch {
    scoreEnabled.value = form.paper_type !== 'yikeyilian'
    fullScore.value = 100
  }
}
const scoreSum = computed(() =>
  form.volume.reduce((s: number, r: any) => s + (Number(r.count) || 0) * (Number(r.score_per) || 0), 0),
)
const scoreMatched = computed(() => !scoreEnabled.value || scoreSum.value === fullScore.value)

function addRow() {
  form.volume.push({ type: '', count: 1, score_per: 1 })
}
function delRow(i: number) {
  form.volume.splice(i, 1)
}

// ===== 卷号范围（多区间）=====
function addRange() {
  const last = ranges.value[ranges.value.length - 1]
  const start = last ? last.end + 1 : 1
  const clamped = planTotal.value ? Math.min(start, planTotal.value) : start
  ranges.value.push({ start: clamped, end: clamped })
}
function delRange(i: number) {
  ranges.value.splice(i, 1)
  if (!ranges.value.length) ranges.value.push({ start: 1, end: 1 })
}

// 卷号范围校验错误（正整数、前<后、不超总卷量、互不重叠）
const rangeErrors = computed<string[]>(() => {
  const errs: string[] = []
  const total = planTotal.value
  for (const r of ranges.value) {
    const s = Number(r.start)
    const e = Number(r.end)
    if (!Number.isInteger(s) || !Number.isInteger(e) || s < 1 || e < 1) {
      errs.push('起止卷号须为正整数')
      continue
    }
    if (e < s) errs.push('区间终止卷号须不小于起始卷号')
    if (total && e > total) errs.push(`卷号区间不得超出总卷量（共 ${total} 套）`)
  }
  const sorted = ranges.value
    .map((r) => ({ s: Number(r.start), e: Number(r.end) }))
    .sort((a, b) => a.s - b.s)
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i].s <= sorted[i - 1].e) {
      errs.push('各卷号区间不得重叠')
      break
    }
  }
  return [...new Set(errs)]
})

// 并集卷数
const unionCount = computed(() => {
  const set = new Set<number>()
  for (const r of ranges.value) {
    const s = Number(r.start)
    const e = Number(r.end)
    if (Number.isInteger(s) && Number.isInteger(e) && s >= 1 && e >= s) {
      for (let i = s; i <= e; i++) set.add(i)
    }
  }
  return set.size
})

function serializeRanges(): string {
  return ranges.value.map((r) => `${Number(r.start)}-${Number(r.end)}`).join(',')
}

// ===== 第一步：基础信息校验 =====
function validateStep1(): boolean {
  if (!form.province.trim()) {
    ElMessage.error('请填写省份')
    return false
  }
  if (form.exam_type_name === '__other__' && !form.exam_type_name_other.trim()) {
    ElMessage.error('请输入考试名称/类型')
    return false
  }
  if (!form.exam_category.trim()) {
    ElMessage.error('请填写考类/专业类别')
    return false
  }
  if (!form.course.trim()) {
    ElMessage.error('请填写课程名')
    return false
  }
  if (form.paper_type === 'yikeyilian') {
    if (!form.textbook.trim()) {
      ElMessage.error('请填写教材名称')
      return false
    }
    if (!form.edition.trim()) {
      ElMessage.error('请填写出版社·版次')
      return false
    }
  }
  return true
}

// 基础信息 → 建/更新草稿项目（拿到 project_id 后第二步才能上传/生成）
function basicBody(extra: Record<string, any> = {}) {
  return {
    paper_type: form.paper_type,
    name: form.name,
    province: form.province,
    exam_type_name: resolvedExamTypeName(),
    exam_category: form.exam_category,
    course: form.course,
    textbook: form.textbook,
    edition: form.edition,
    plan_source: form.plan_source,
    ...extra,
  }
}

async function ensureDraft() {
  if (projectId.value) {
    await api.updateProject(projectId.value, basicBody({ paper_range: 'all', status: 'draft' }))
  } else {
    const p: any = await api.createProject(basicBody({ paper_range: 'all', status: 'draft' }))
    projectId.value = p.id
  }
}

const advancing = ref(false)
async function goToStep2() {
  if (!validateStep1()) return
  advancing.value = true
  try {
    await ensureDraft()
    currentStep.value = 1
    loadResources()
  } catch {
    /* 错误已由全局拦截器提示 */
  } finally {
    advancing.value = false
  }
}

// ===== 第二步：资料上传 + 规划表生成 =====
const uploadUrl = computed(() => (projectId.value ? api.uploadResourceUrl(projectId.value) : ''))
const resources = ref<any[]>([])
async function loadResources() {
  if (!projectId.value) return
  try {
    resources.value = await api.listResources(projectId.value)
  } catch {
    /* 忽略 */
  }
}
async function onUploadSuccess() {
  ElMessage.success('上传成功')
  await loadResources()
  // 上传规划表分支：上传即自动解析出总卷量，无需再点“生成规划表”
  if (form.plan_source === 'upload') await generatePlan()
}

const generating = ref(false)
const planResult = ref<any>(null)
async function generatePlan() {
  if (!projectId.value) return ElMessage.error('请先完成第一步')
  generating.value = true
  try {
    const res: any = await api.generatePlan(projectId.value, form.plan_source)
    planResult.value = res
    planTotal.value = res.total || 0
    // 生成后默认卷号范围覆盖全部
    ranges.value = [{ start: 1, end: Math.max(1, planTotal.value) }]
    if (res.warnings && res.warnings.length) ElMessage.warning(res.warnings.join('；'))
    ElMessage.success(`规划表已生成，总卷量 ${planTotal.value} 套`)
  } finally {
    generating.value = false
  }
}

async function goToStep3() {
  // 上传模式：下一步时若尚未解析出总卷量，则先解析已上传的规划表
  if (form.plan_source === 'upload' && planTotal.value <= 0) {
    try {
      await generatePlan()
    } catch {
      return
    }
  }
  if (planTotal.value <= 0) {
    return ElMessage.error(
      form.plan_source === 'upload'
        ? '未能从规划表解析出总卷量，请确认已上传规划表 xlsx'
        : '请先生成规划表以确定总卷量',
    )
  }
  currentStep.value = 2
}

function goPrev() {
  if (currentStep.value > 0) currentStep.value--
}

// ===== 第三步：卷号范围 + 配置，保存并创建 =====
const saving = ref(false)
async function submit() {
  if (planTotal.value <= 0) return ElMessage.error('请先在第二步生成规划表')
  if (rangeErrors.value.length) return ElMessage.error(rangeErrors.value[0])
  if (unionCount.value <= 0) return ElMessage.error('请设置至少一个有效卷号范围')
  if (diffSum.value !== 100) return ElMessage.error('难度分布三者之和必须为 100')
  if (form.volume.some((r: any) => !r.type)) return ElMessage.error('请为每个题型行选择题型')
  if (!scoreMatched.value)
    return ElMessage.error(`题型分值合计为 ${scoreSum.value} 分，与该系列满分 ${fullScore.value} 分不一致`)
  if (form.volume.some((r: any) => isRowInvalid(r)))
    return ElMessage.error('存在当前考类不支持的题型（已高亮），请重新选择')
  if (!form.output_versions.length) return ElMessage.error('至少选择一个输出版本')
  saving.value = true
  try {
    const by_type: Record<string, any> = {}
    for (const r of form.volume) by_type[r.type] = { count: Number(r.count), score_per: Number(r.score_per) }
    const body = basicBody({
      paper_range: serializeRanges(),
      output_versions: form.output_versions,
      status: 'ready',
      volume_config: {
        by_type,
        difficulty: form.difficulty,
        narrow_point: form.narrow_point,
        exam_minutes: Number(form.exam_minutes) || 60,
      },
      ai_options: form.ai,
    })
    await api.updateProject(projectId.value, body)
    clearDraft()
    ElMessage.success('项目已创建')
    router.push(`/projects/${projectId.value}/flow`)
  } finally {
    saving.value = false
  }
}

// ===== 管理题型弹窗：按考类/课程展示题型库，内置只读、自定义可增删 =====
interface TypeGroup {
  id: string
  name: string
  builtin_types: string[]
  custom_types: string[]
  input: string
}
const mgrVisible = ref(false)
const mgrLoading = ref(false)
const mgrGroups = ref<TypeGroup[]>([])
let mgrDirty = false

async function openManager() {
  mgrVisible.value = true
  mgrLoading.value = true
  mgrDirty = false
  try {
    const res: any = await api.getTypeLibrary(form.paper_type)
    mgrGroups.value = (res?.groups || []).map((g: any) => ({
      id: g.id,
      name: g.name,
      builtin_types: g.builtin_types || [],
      custom_types: g.custom_types || [],
      input: '',
    }))
  } finally {
    mgrLoading.value = false
  }
}

async function persistGroup(g: TypeGroup) {
  try {
    await api.saveCustomTypes(form.paper_type, g.id, g.custom_types)
    mgrDirty = true
  } catch {
    /* 拦截器已提示 */
  }
}

async function addTypeInGroup(g: TypeGroup) {
  const name = ensureQuestionSuffix(g.input || '')
  if (!name) return
  if (g.builtin_types.includes(name) || g.custom_types.includes(name)) {
    ElMessage.warning('该题型已存在')
    g.input = ''
    return
  }
  g.custom_types.push(name)
  g.input = ''
  await persistGroup(g)
}

async function removeTypeInGroup(g: TypeGroup, name: string) {
  g.custom_types = g.custom_types.filter((t) => t !== name)
  await persistGroup(g)
}

function onManagerClosed() {
  // 管理期间若有改动，刷新当前下拉，使新增/删除立即生效
  if (mgrDirty) loadQuestionTypes()
  mgrDirty = false
}

onMounted(() => {
  // 有草稿则整体恢复（含 paper_type/步骤/项目 id）；没有草稿再回退到 URL 参数
  const restored = loadDraft()
  if (!restored && route.query.type) form.paper_type = route.query.type as string
  loadQuestionTypes()
  loadFullScore()
  if (projectId.value) loadResources()
})
</script>

<template>
  <el-card>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>项目创建</span>
        <el-button size="small" @click="openManager">管理题型</el-button>
      </div>
    </template>
    <el-form label-width="120px" style="max-width: 920px">
      <el-steps :active="currentStep" finish-status="success" align-center class="wizard-steps">
        <el-step title="第一步" description="基础信息" />
        <el-step title="第二步" description="资料与规划表" />
        <el-step title="第三步" description="卷号范围与配置" />
      </el-steps>

      <!-- ============ 第一步：基础信息 ============ -->
      <div v-show="currentStep === 0">
        <el-form-item label="卷类产品">
          <div style="display: flex; gap: 12px; flex-wrap: wrap">
            <el-card
              v-for="t in TYPES"
              :key="t.value"
              shadow="hover"
              :style="{
                width: '220px',
                cursor: 'pointer',
                border: form.paper_type === t.value ? '2px solid #409eff' : '1px solid #eee',
              }"
              @click="form.paper_type = t.value"
            >
              <strong>{{ t.label }}</strong>
              <div style="color: #888; font-size: 12px; margin-top: 6px">{{ t.desc }}</div>
            </el-card>
          </div>
        </el-form-item>

        <el-form-item label="项目名称">
          <el-input v-model="form.name" placeholder="可留空自动生成" />
        </el-form-item>
        <el-form-item label="省份（全称）" required>
          <el-input v-model="form.province" placeholder="如 内蒙古自治区（自治区不简写）" />
        </el-form-item>
        <el-form-item label="考试名称/类型" required>
          <el-select v-model="form.exam_type_name" filterable default-first-option style="width: 260px">
            <el-option label="高职分类考试" value="高职分类考试" />
            <el-option label="对口招生" value="对口招生" />
            <el-option label="春季高考" value="春季高考" />
            <el-option label="其他名称" value="__other__" />
          </el-select>
          <el-input
            v-if="form.exam_type_name === '__other__'"
            v-model="form.exam_type_name_other"
            placeholder="请输入考试名称/类型"
            style="width: 260px; margin-left: 12px"
          />
        </el-form-item>
        <el-form-item label="考类/专业类别" required>
          <el-input v-model="form.exam_category" placeholder="如 机电类/土建类/汽修类" />
        </el-form-item>
        <el-form-item label="课程名" required>
          <el-input v-model="form.course" />
        </el-form-item>
        <el-form-item label="教材名称" required v-if="form.paper_type === 'yikeyilian'">
          <el-input v-model="form.textbook" placeholder="如 电工基础" />
        </el-form-item>
        <el-form-item label="出版社·版次" required v-if="form.paper_type === 'yikeyilian'">
          <el-input v-model="form.edition" placeholder="如 高教版·第三版" />
        </el-form-item>
        <el-form-item label="考试时长（分钟）" v-if="scoreEnabled">
          <el-input-number v-model="form.exam_minutes" :min="1" size="small" style="width: 120px" />
          <span style="margin-left: 12px; color: #888; font-size: 12px">卷首“时间：X分钟”，默认 60</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="advancing" @click="goToStep2">下一步</el-button>
        </el-form-item>
      </div>

      <!-- ============ 第二步：资料上传 + 规划表生成 ============ -->
      <div v-show="currentStep === 1">
        <el-form-item label="规划表来源">
          <el-radio-group v-model="form.plan_source">
            <el-radio value="ocr">本地生成（上传考纲/真题/教材，OCR 扫描合成）</el-radio>
            <el-radio value="upload">上传规划表 xlsx</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="上传资料">
          <div style="display: flex; gap: 16px; flex-wrap: wrap">
            <template v-if="form.plan_source === 'ocr'">
              <el-card v-for="k in ['考纲', '教材', '真题']" :key="k" style="width: 200px" shadow="never">
                <div style="margin-bottom: 8px"><strong>{{ k }}</strong></div>
                <el-upload
                  :action="uploadUrl"
                  :data="{ kind: k }"
                  name="file"
                  :on-success="onUploadSuccess"
                  :show-file-list="false"
                >
                  <el-button size="small">选择文件上传</el-button>
                </el-upload>
              </el-card>
            </template>
            <template v-else>
              <el-card style="width: 220px" shadow="never">
                <div style="margin-bottom: 8px"><strong>规划表（xlsx）</strong></div>
                <el-upload
                  :action="uploadUrl"
                  :data="{ kind: '规划表' }"
                  name="file"
                  accept=".xlsx"
                  :on-success="onUploadSuccess"
                  :show-file-list="false"
                >
                  <el-button size="small" :loading="generating">选择规划表上传</el-button>
                </el-upload>
              </el-card>
            </template>
          </div>
        </el-form-item>

        <!-- 本地生成分支才需要手动生成；上传规划表分支上传后自动解析总卷量 -->
        <el-form-item v-if="form.plan_source === 'ocr'" label="生成规划表">
          <el-button type="primary" :loading="generating" @click="generatePlan">
            {{ planTotal > 0 ? '重新生成规划表' : '生成规划表' }}
          </el-button>
          <el-tag v-if="planTotal > 0" type="success" style="margin-left: 12px">
            总卷量 {{ planTotal }} 套
          </el-tag>
          <span style="margin-left: 12px; color: #888; font-size: 12px">
            将根据考纲/真题/教材生成 规划表、映射表{{ form.paper_type === 'kaogang_100' ? '、细目表' : '' }}
          </span>
        </el-form-item>

        <el-form-item v-if="form.plan_source === 'upload' && planTotal > 0" label="总卷量">
          <el-tag type="success">{{ planTotal }} 套</el-tag>
        </el-form-item>

        <el-form-item v-if="planResult" label="生成产物">
          <div style="font-size: 13px; line-height: 1.8">
            <div>规划表：{{ planResult.plan_file }}</div>
            <div v-if="planResult.mapping_file">映射表：{{ planResult.mapping_file }}</div>
            <div v-if="planResult.mesh_files && planResult.mesh_files.length">
              细目表：{{ planResult.mesh_files.join('、') }}
            </div>
            <div
              v-for="(w, i) in planResult.warnings || []"
              :key="i"
              style="color: var(--el-color-warning)"
            >
              {{ w }}
            </div>
          </div>
        </el-form-item>

        <el-form-item v-if="form.plan_source === 'upload' && resources.length" label="已上传资料">
          <el-table :data="resources" size="small" style="width: 560px">
            <el-table-column prop="kind" label="类型" width="100" />
            <el-table-column prop="filename" label="文件名" min-width="240" />
          </el-table>
        </el-form-item>

        <el-form-item>
          <el-button @click="goPrev">上一步</el-button>
          <el-button type="primary" @click="goToStep3">下一步</el-button>
        </el-form-item>
      </div>

      <!-- ============ 第三步：卷号范围 + 配置 ============ -->
      <div v-show="currentStep === 2">
        <el-form-item label="卷号范围">
          <div>
            <div style="margin-bottom: 8px; color: #888; font-size: 12px">
              本项目总卷量 {{ planTotal }} 套；各区间起止卷号须为正整数，终止不小于起始（可相同表示单卷），且区间之间不得重叠。
            </div>
            <div
              v-for="(r, i) in ranges"
              :key="i"
              style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px"
            >
              <el-input-number v-model="r.start" :min="1" :max="planTotal || undefined" size="small" style="width: 120px" />
              <span>-</span>
              <el-input-number v-model="r.end" :min="1" :max="planTotal || undefined" size="small" style="width: 120px" />
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                :disabled="ranges.length <= 1"
                @click="delRange(i)"
              />
            </div>
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px">
              <el-button size="small" @click="addRange">+ 增加范围</el-button>
              <el-tag type="success">将生成 {{ unionCount }} 套</el-tag>
            </div>
            <div
              v-for="(e, i) in rangeErrors"
              :key="'e' + i"
              style="color: var(--el-color-danger); font-size: 12px; margin-top: 4px"
            >
              {{ e }}
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="scoreEnabled ? '题型/题量/分值' : '题型/题量'">
          <el-table :data="form.volume" size="small" :style="{ width: scoreEnabled ? '640px' : '490px' }">
            <el-table-column label="题型">
              <template #default="{ row }">
                <el-select
                  v-model="row.type"
                  size="small"
                  placeholder="请选择题型"
                  style="width: 100%"
                  :class="{ 'qt-invalid': isRowInvalid(row) }"
                  @change="(val: string) => onTypeChange(row, val)"
                >
                  <el-option v-for="qt in allTypes" :key="qt" :label="qt" :value="qt" />
                  <el-option v-if="isRowInvalid(row)" :key="row.type" :label="`${row.type}（不适用）`" :value="row.type" />
                  <el-option :key="CUSTOM_OPTION" label="+ 自定义题型…" :value="CUSTOM_OPTION" />
                </el-select>
                <div v-if="isRowInvalid(row)" class="qt-invalid-tip">当前考类不支持，请重新选择</div>
              </template>
            </el-table-column>
            <el-table-column label="题量" width="150">
              <template #default="{ row }"><el-input-number v-model="row.count" :min="0" size="small" style="width: 120px" /></template>
            </el-table-column>
            <el-table-column v-if="scoreEnabled" label="分值" width="150">
              <template #default="{ row }"><el-input-number v-model="row.score_per" :min="0" size="small" style="width: 120px" /></template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ $index }">
                <el-button size="small" type="danger" :icon="Delete" @click="delRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 8px; display: flex; align-items: center; gap: 12px">
            <el-button size="small" @click="addRow">+ 增加题型</el-button>
            <template v-if="scoreEnabled">
              <el-tag :type="scoreMatched ? 'success' : 'danger'">
                分值合计 {{ scoreSum }} / 满分 {{ fullScore }}
              </el-tag>
              <span v-if="!scoreMatched" style="color: var(--el-color-danger); font-size: 12px">
                需等于满分才能创建（满分在「产品系列专属配置」里修改）
              </span>
            </template>
            <el-tag v-else type="info">一课一练不标注分数</el-tag>
          </div>
        </el-form-item>

        <el-form-item label="难度分布">
          <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px">
            <span>简单</span>
            <el-input-number v-model="form.difficulty.easy" :min="0" :max="100" size="small" style="width: 120px" />
            <span>适中</span>
            <el-input-number v-model="form.difficulty.medium" :min="0" :max="100" size="small" style="width: 120px" />
            <span>困难</span>
            <el-input-number v-model="form.difficulty.hard" :min="0" :max="100" size="small" style="width: 120px" />
            <el-tag :type="diffSum === 100 ? 'success' : 'danger'" style="margin-left: 4px">合计 {{ diffSum }}</el-tag>
          </div>
        </el-form-item>

        <el-form-item label="窄考点合并">
          <el-switch v-model="form.narrow_point.enabled" />
          <span style="margin: 0 8px">阈值</span>
          <el-input-number v-model="form.narrow_point.merge_threshold" :min="0" size="small" />
        </el-form-item>

        <el-form-item label="输出版本">
          <el-checkbox-group v-model="form.output_versions">
            <el-checkbox value="原卷版">原卷版</el-checkbox>
            <el-checkbox value="解析版">解析版</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="AI 辅助">
          <el-switch v-model="form.ai.match" active-text="匹配" />
          <el-switch v-model="form.ai.summary" active-text="摘要" style="margin-left: 12px" />
          <el-switch v-model="form.ai.fill" active-text="补题" style="margin-left: 12px" />
        </el-form-item>
        <el-form-item label="信度阈值">
          <el-input-number v-model="form.ai.match_threshold" :min="0" :max="1" :step="0.05" size="small" />
        </el-form-item>
        <el-form-item label="修复轮数">
          <el-input-number v-model="form.ai.max_fix_rounds" :min="0" size="small" />
        </el-form-item>

        <el-form-item>
          <el-button @click="goPrev">上一步</el-button>
          <el-button type="primary" :loading="saving" :disabled="rangeErrors.length > 0" @click="submit">
            保存并创建
          </el-button>
        </el-form-item>
      </div>
    </el-form>

    <el-dialog
      v-model="mgrVisible"
      title="管理题型"
      width="720px"
      @closed="onManagerClosed"
    >
      <div style="color: #888; font-size: 12px; margin-bottom: 12px">
        灰色为内置题型（只读）；自定义题型仅本机保存、自动以“题”结尾，删除/新增后立即生效。按考类/课程分别维护。
      </div>
      <div v-loading="mgrLoading" style="max-height: 60vh; overflow-y: auto">
        <div
          v-for="g in mgrGroups"
          :key="g.id"
          style="border: 1px solid #eee; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px"
        >
          <div style="font-weight: 600; margin-bottom: 8px">{{ g.name }}</div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center">
            <el-tag v-for="t in g.builtin_types" :key="'b-' + t" type="info">{{ t }}</el-tag>
            <el-tag
              v-for="t in g.custom_types"
              :key="'c-' + t"
              type="success"
              closable
              @close="removeTypeInGroup(g, t)"
            >{{ t }}</el-tag>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 10px">
            <el-input
              v-model="g.input"
              size="small"
              placeholder="输入自定义题型（如 名词解释）"
              style="width: 240px"
              @keyup.enter="addTypeInGroup(g)"
            />
            <el-button size="small" type="primary" plain @click="addTypeInGroup(g)">添加</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="mgrVisible = false">完成</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
/* 三步向导指示器：脱离表单 920px 限制，居中并整体放大 */
.wizard-steps {
  max-width: 720px;
  margin: 8px auto 32px;
}
.wizard-steps :deep(.el-step__icon) {
  width: 44px;
  height: 44px;
  font-size: 20px;
}
.wizard-steps :deep(.el-step__title) {
  font-size: 18px;
  font-weight: 600;
}
.wizard-steps :deep(.el-step__description) {
  font-size: 14px;
}

/* 失效题型行高亮：兼容 Element Plus 新旧 select 包裹元素 */
.qt-invalid :deep(.el-select__wrapper),
.qt-invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}
.qt-invalid-tip {
  margin-top: 2px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.2;
}
</style>
