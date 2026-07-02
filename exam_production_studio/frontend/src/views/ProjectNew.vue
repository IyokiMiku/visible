<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRawFile } from 'element-plus'
import { Delete, Document, UploadFilled } from '@element-plus/icons-vue'
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
  // 学科网映射（仅用于拉题课程映射，不参与命名）：大类id / 专业id / 课程courseId
  xueke_big_id: '' as number | '',
  xueke_profession_id: '' as number | '',
  xueke_course_id: '' as number | '',
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

// 解析已存储的卷号范围字符串（如 "1-3,5"）为区间数组；非法/空段忽略。
function parseRangesFromStr(s: string): { start: number; end: number }[] {
  const out: { start: number; end: number }[] = []
  for (const part of (s || '').split(',')) {
    const t = part.trim()
    if (!t) continue
    const seg = t.split('-')
    const a = Number(seg[0])
    const b = seg.length > 1 ? Number(seg[1]) : a
    if (Number.isInteger(a) && Number.isInteger(b) && a >= 1 && b >= a) out.push({ start: a, end: b })
  }
  return out
}

// 「继续创建」：按项目 id 从后端载入草稿，回填表单/卷号范围/总卷量，从第一步开始续建。
// 与 sessionStorage 草稿不同——这里针对列表里明确选中的某个草稿项目，优先级更高。
async function loadServerDraft(id: string): Promise<void> {
  // restoring 期间抑制 paper_type watcher 对 volume 的重置（与 loadDraft 一致）
  restoring = true
  try {
    const p: any = await api.getProject(id)
    projectId.value = id
    form.paper_type = p.paper_type || form.paper_type
    form.name = p.name || ''
    form.province = p.province || ''
    form.exam_category = p.exam_category || ''
    form.course = p.course || ''
    form.textbook = p.textbook || ''
    form.edition = p.edition || ''
    form.plan_source = p.plan_source || 'ocr'
    // 考试名称：命中固定选项直接选中，否则归入「其他名称」并填入自定义框
    const known = ['高职分类考试', '对口招生', '春季高考']
    if (p.exam_type_name && !known.includes(p.exam_type_name)) {
      form.exam_type_name = '__other__'
      form.exam_type_name_other = p.exam_type_name
    } else {
      form.exam_type_name = p.exam_type_name || '高职分类考试'
      form.exam_type_name_other = ''
    }
    const vc = p.volume_config || {}
    if (vc.by_type && Object.keys(vc.by_type).length) {
      form.volume = Object.entries(vc.by_type).map(([type, v]: any) => ({
        type,
        count: Number(v?.count) || 0,
        score_per: Number(v?.score_per) || 0,
      }))
    }
    if (vc.difficulty) form.difficulty = { ...form.difficulty, ...vc.difficulty }
    if (vc.narrow_point) form.narrow_point = { ...form.narrow_point, ...vc.narrow_point }
    if (vc.exam_minutes) form.exam_minutes = Number(vc.exam_minutes) || 60
    if (Array.isArray(p.output_versions) && p.output_versions.length) form.output_versions = p.output_versions
    const ai = p.ai_options || {}
    form.ai = {
      match: ai.match ?? true,
      summary: ai.summary ?? true,
      fill: ai.fill ?? true,
      match_threshold: ai.match_threshold ?? 0.85,
      max_fix_rounds: ai.max_fix_rounds ?? 2,
    }
    if (ai.xueke_big_id) form.xueke_big_id = Number(ai.xueke_big_id)
    if (ai.xueke_profession_id) form.xueke_profession_id = Number(ai.xueke_profession_id)
    if (ai.xueke_course_id) form.xueke_course_id = Number(ai.xueke_course_id)
    // 恢复总卷量（此前已生成/上传过规划表才有值，否则为 0，需回到第二步重新生成）
    try {
      const pl: any = await api.getPlan(id)
      planTotal.value = Number(pl?.total) || 0
    } catch {
      planTotal.value = 0
    }
    // 卷号范围：非 all 时按存储恢复；否则默认覆盖全部
    const parsed = p.paper_range && p.paper_range !== 'all' ? parseRangesFromStr(p.paper_range) : []
    ranges.value = parsed.length ? parsed : [{ start: 1, end: Math.max(1, planTotal.value) }]
    // 恢复上次停留步；若记为第三步但规划表总卷量已丢失（未生成/被清），退回第二步重新生成
    let step = Number.isInteger(p.wizard_step) ? Number(p.wizard_step) : 0
    if (step >= 2 && planTotal.value <= 0) step = 1
    currentStep.value = Math.min(2, Math.max(0, step))
  } finally {
    nextTick(() => {
      restoring = false
    })
  }
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
// 步骤变化：写本地临时草稿，并在有项目 id 时把「停留步」记到后端（续建定位用）；
// restoring 期间（载入草稿时）不回写，避免把刚读出的步骤覆盖成 0。
watch(currentStep, (s) => {
  saveDraft()
  if (!restoring && projectId.value) persistStep(s)
})
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

// ===== 学科网「大类 → 专业 → 课程」级联（仅用于拉题课程映射，不参与命名）=====
interface XkCourse { courseId: number; courseName: string }
interface XkProfession { id: number; name: string; courses: XkCourse[] }
interface XkCategory { id: number; name: string; professions: XkProfession[] }
const xuekeCategories = ref<XkCategory[]>([])

async function loadXuekeTree() {
  try {
    const res: any = await api.getXuekeTree()
    xuekeCategories.value = (res && res.categories) || []
  } catch {
    xuekeCategories.value = []
  }
}

const xuekeProfessions = computed<XkProfession[]>(() => {
  const cat = xuekeCategories.value.find((c) => c.id === form.xueke_big_id)
  return cat ? cat.professions || [] : []
})
const xuekeCourses = computed<XkCourse[]>(() => {
  const prof = xuekeProfessions.value.find((p) => p.id === form.xueke_profession_id)
  return prof ? prof.courses || [] : []
})

// 切换大类：清空下级专业/课程选择
function onXuekeBigChange() {
  form.xueke_profession_id = ''
  form.xueke_course_id = ''
}
// 切换专业：清空下级课程选择
function onXuekeProfessionChange() {
  form.xueke_course_id = ''
}
// 选中学科网课程：若「课程名」手填框为空，用学科网课程名兜底预填（各省叫法不同时用户可再改）
function onXuekeCourseChange(courseId: number) {
  const c = xuekeCourses.value.find((x) => x.courseId === courseId)
  if (c && !form.course.trim()) form.course = c.courseName
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
  // 走到第二步即停留步=1，随草稿一并落库，便于「继续创建」定位
  if (projectId.value) {
    await api.updateProject(projectId.value, basicBody({ paper_range: 'all', status: 'draft', wizard_step: 1 }))
  } else {
    const p: any = await api.createProject(basicBody({ paper_range: 'all', status: 'draft', wizard_step: 1 }))
    projectId.value = p.id
  }
}

// 记住向导「停留步」：写回后端草稿（仅在已有项目 id 时）。失败不阻塞操作。
async function persistStep(step: number) {
  if (!projectId.value) return
  try {
    await api.updateProject(projectId.value, basicBody({ status: 'draft', wizard_step: step }))
  } catch {
    /* 步骤记忆失败不影响创建流程，忽略 */
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

// 各资料类型允许的扩展名（与后端 resources.py 白名单保持一致）。
const ACCEPT_MAP: Record<string, string> = {
  考纲: '.doc,.docx,.pdf',
  教材: '.doc,.docx,.pdf',
  真题: '.doc,.docx,.pdf',
  规划表: '.xlsx',
}
function acceptOf(kind: string): string {
  return ACCEPT_MAP[kind] || ''
}
function extHintOf(kind: string): string {
  return kind === '规划表' ? 'xlsx' : 'docx / pdf'
}

// 各卷类在「本地生成(OCR)」下必须上传的资料类型：
// 一课一练→考纲+教材；考纲百套卷/考点双析卷→考纲；其余（真题等）非必传。
const REQUIRED_KINDS: Record<string, string[]> = {
  yikeyilian: ['考纲', '教材'],
  kaogang_100: ['考纲'],
  shuangxi: ['考纲'],
}
function isRequiredKind(kind: string): boolean {
  return (REQUIRED_KINDS[form.paper_type] || []).includes(kind)
}

// 按类型分组当前已上传资料，供各上传框内直接展示
const resourcesByKind = computed<Record<string, any[]>>(() => {
  const map: Record<string, any[]> = {}
  for (const r of resources.value) {
    const k = r.kind || '其他'
    ;(map[k] ||= []).push(r)
  }
  return map
})

async function loadResources() {
  if (!projectId.value) return
  try {
    resources.value = await api.listResources(projectId.value)
  } catch {
    /* 忽略 */
  }
}

// 拖拽/选择上传前校验扩展名（拖拽可绕过 accept，需前端二次拦截）
function beforeUpload(kind: string, file: UploadRawFile): boolean {
  const name = (file.name || '').toLowerCase()
  const allowed = acceptOf(kind)
    .split(',')
    .map((e) => e.trim())
    .filter(Boolean)
  const ok = allowed.some((ext) => name.endsWith(ext))
  if (!ok) {
    ElMessage.error(`「${kind}」仅支持 ${allowed.join('、')} 格式`)
    return false
  }
  // 规划表最多一个：已存在时先删除再上传，避免多份并存
  if (kind === '规划表' && (resourcesByKind.value['规划表'] || []).length) {
    ElMessage.warning('规划表最多只允许上传一个，请先删除已上传的规划表')
    return false
  }
  return true
}

async function onUploadSuccess(_resp: any, file: any) {
  ElMessage.success(`「${file?.name || '文件'}」上传成功`)
  await loadResources()
  // 上传规划表分支：上传即自动解析出总卷量，无需再点“生成规划表”
  if (form.plan_source === 'upload') await generatePlan()
}

function onUploadError() {
  ElMessage.error('上传失败，请检查文件格式或重试')
}

async function deleteResource(r: any) {
  try {
    await ElMessageBox.confirm(`确定删除「${r.filename}」吗？`, '删除资料', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await api.deleteResource(projectId.value, r.id)
    ElMessage.success('已删除')
    await loadResources()
  } catch {
    /* 拦截器已提示 */
  }
}

// 校验必传资料是否齐全（仅本地生成 OCR 分支适用）
function validateRequiredUploads(): boolean {
  const required = REQUIRED_KINDS[form.paper_type] || []
  const missing = required.filter((k) => !(resourcesByKind.value[k] || []).length)
  if (missing.length) {
    ElMessage.error(`请先上传：${missing.join('、')}`)
    return false
  }
  return true
}

const generating = ref(false)
const planResult = ref<any>(null)
// force=true 表示「重新生成」（无视缓存重跑 OCR/合成）；默认 false 时本地生成会复用已有产物。
async function generatePlan(force = false) {
  if (!projectId.value) return ElMessage.error('请先完成第一步')
  if (form.plan_source === 'ocr' && !validateRequiredUploads()) return
  generating.value = true
  try {
    const res: any = await api.generatePlan(projectId.value, form.plan_source, force)
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

// 按某来源已有产物物化卷量（绝不重跑 OCR）：上传→解析已传 xlsx；本地生成→命中缓存。
// 该来源无产物时返回 false（不生成占位），由调用方提示去上传/生成。
async function materializeSource(src: string): Promise<boolean> {
  if (!projectId.value) return false
  const st: any = await api.planStatus(projectId.value, src)
  if (!st?.exists) return false
  const res: any = await api.generatePlan(projectId.value, src, false)
  planResult.value = res
  planTotal.value = res.total || 0
  ranges.value = [{ start: 1, end: Math.max(1, planTotal.value) }]
  return planTotal.value > 0
}

// 切换规划表来源：只做「只读探测 + 刷新显示」，绝不触发任何生成/落库/OCR。
// 用户可能只是想切过来看看，因此这里无副作用；真正物化在「生成/上传/下一步」时才发生。
async function onPlanSourceChange(src: string) {
  // 先清零，避免残留另一来源的旧卷量造成「到底用哪个」的困惑
  planResult.value = null
  planTotal.value = 0
  ranges.value = [{ start: 1, end: 1 }]
  if (!projectId.value) return
  try {
    const st: any = await api.planStatus(projectId.value, src) // 只读，不生成
    if (st?.exists) {
      planTotal.value = st.total || 0
      ranges.value = [{ start: 1, end: Math.max(1, planTotal.value) }]
    }
  } catch {
    /* 忽略：错误已由全局拦截器提示 */
  }
}

async function goToStep3() {
  // 一律以「当前选择的来源」为准重新物化卷量：上传→重新解析已传 xlsx；本地生成→复用缓存。
  // 这样即便界面上残留了另一来源的旧卷量，也不会被误用。
  let ok = false
  try {
    ok = await materializeSource(form.plan_source)
  } catch {
    return
  }
  if (!ok) {
    return ElMessage.error(
      form.plan_source === 'upload'
        ? '未识别到有效规划表，请先上传规划表 xlsx'
        : '请先点击「生成规划表」以确定总卷量',
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
      // 学科网 courseId 随 ai_options 落库，拉题时 pull_for_plan 优先读取 xueke_course_id
      ai_options: {
        ...form.ai,
        ...(form.xueke_course_id ? { xueke_course_id: Number(form.xueke_course_id) } : {}),
        ...(form.xueke_big_id ? { xueke_big_id: Number(form.xueke_big_id) } : {}),
        ...(form.xueke_profession_id ? { xueke_profession_id: Number(form.xueke_profession_id) } : {}),
      },
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

onMounted(async () => {
  // ?draft=<id>：从列表「继续创建」进入，优先按项目 id 载入该草稿（忽略 sessionStorage 临时草稿）
  const draftId = route.query.draft as string | undefined
  if (draftId) {
    clearDraft()
    await loadServerDraft(draftId)
  } else {
    // 有临时草稿则整体恢复（含 paper_type/步骤/项目 id）；没有再回退到 URL type 参数
    const restored = loadDraft()
    if (!restored && route.query.type) form.paper_type = route.query.type as string
  }
  loadQuestionTypes()
  loadXuekeTree()
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
    <el-form label-width="120px" style="max-width: 1180px">
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
          <el-input v-model="form.name" placeholder="可留空自动生成" style="width: 480px" />
        </el-form-item>
        <el-form-item label="省份（全称）" required>
          <el-input v-model="form.province" placeholder="如 内蒙古自治区（自治区不简写）" style="width: 480px" />
        </el-form-item>
        <el-form-item label="考试名称/类型" required>
          <el-select v-model="form.exam_type_name" filterable default-first-option style="width: 300px">
            <el-option label="高职分类考试" value="高职分类考试" />
            <el-option label="对口招生" value="对口招生" />
            <el-option label="春季高考" value="春季高考" />
            <el-option label="其他名称" value="__other__" />
          </el-select>
          <el-input
            v-if="form.exam_type_name === '__other__'"
            v-model="form.exam_type_name_other"
            placeholder="请输入考试名称/类型"
            style="width: 300px; margin-left: 12px"
          />
        </el-form-item>
        <el-form-item label="考类/专业类别" required>
          <el-input v-model="form.exam_category" placeholder="如 机电类/土建类/汽修类" style="width: 480px" />
        </el-form-item>
        <el-form-item label="课程名" required>
          <el-input v-model="form.course" placeholder="仅用于文档与输出文件夹命名，不参与拉题" style="width: 480px" />
          <div style="color: #888; font-size: 12px; margin-top: 4px">
            此名称只用于命名（文档标题、输出文件夹等），<strong>不决定拉题</strong>；实际拉题按下方选择的学科网课程。
          </div>
        </el-form-item>
        <el-form-item label="学科网课程（拉题依据）">
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center">
            <el-select
              v-model="form.xueke_big_id"
              filterable
              clearable
              placeholder="专业大类"
              style="width: 200px"
              @change="onXuekeBigChange"
            >
              <el-option v-for="c in xuekeCategories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select
              v-model="form.xueke_profession_id"
              filterable
              clearable
              placeholder="专业"
              :disabled="!form.xueke_big_id"
              style="width: 200px"
              @change="onXuekeProfessionChange"
            >
              <el-option v-for="p in xuekeProfessions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-select
              v-model="form.xueke_course_id"
              filterable
              clearable
              placeholder="课程"
              :disabled="!form.xueke_profession_id"
              style="width: 240px"
              @change="onXuekeCourseChange"
            >
              <el-option
                v-for="c in xuekeCourses"
                :key="c.courseId"
                :label="c.courseName"
                :value="c.courseId"
              />
            </el-select>
          </div>
          <div style="color: #888; font-size: 12px; margin-top: 4px">
            <strong>这里选择的课程才是实际拉题的依据</strong>（对应学科网 courseId）。各省考类/课程叫法可能与学科网不同，命名请用上面手填的考类与课程名。
          </div>
          <div v-if="!form.xueke_course_id" style="color: var(--el-color-warning); font-size: 12px; margin-top: 2px">
            未选择学科网课程时将无法按题库拉题，只能走 AI 补题。
          </div>
        </el-form-item>
        <el-form-item label="教材名称" required v-if="form.paper_type === 'yikeyilian'">
          <el-input v-model="form.textbook" placeholder="如 电工基础" style="width: 480px" />
        </el-form-item>
        <el-form-item label="出版社·版次" required v-if="form.paper_type === 'yikeyilian'">
          <el-input v-model="form.edition" placeholder="如 高教版·第三版" style="width: 480px" />
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
          <el-radio-group v-model="form.plan_source" @change="onPlanSourceChange">
            <el-radio value="ocr">本地生成（上传考纲/真题/教材，OCR 扫描合成）</el-radio>
            <el-radio value="upload">上传规划表 xlsx</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="上传资料">
          <div class="upload-row">
            <el-card
              v-for="k in form.plan_source === 'ocr' ? ['考纲', '教材', '真题'] : ['规划表']"
              :key="k"
              class="upload-card"
              shadow="never"
            >
              <div class="upload-card__title">
                <span class="upload-card__name">
                  <strong>{{ k }}</strong>
                  <el-tag
                    v-if="k !== '规划表'"
                    :type="isRequiredKind(k) ? 'danger' : 'info'"
                    size="small"
                    effect="light"
                    round
                  >{{ isRequiredKind(k) ? '必传' : '选传' }}</el-tag>
                </span>
                <span class="upload-card__hint">支持 {{ extHintOf(k) }}</span>
              </div>
              <el-upload
                drag
                :action="uploadUrl"
                :data="{ kind: k }"
                name="file"
                :accept="acceptOf(k)"
                :multiple="k !== '规划表'"
                :before-upload="(file: any) => beforeUpload(k, file)"
                :on-success="onUploadSuccess"
                :on-error="onUploadError"
                :show-file-list="false"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  拖拽文件到此处，或<em>点击上传</em>
                </div>
              </el-upload>

              <!-- 已上传文件在框内明确展示，避免误认为无反应 -->
              <div class="upload-card__files">
                <template v-if="(resourcesByKind[k] || []).length">
                  <div v-for="r in resourcesByKind[k]" :key="r.id" class="upload-file">
                    <el-icon class="upload-file__icon"><Document /></el-icon>
                    <span class="upload-file__name" :title="r.filename">{{ r.filename }}</span>
                    <el-icon class="upload-file__del" title="删除" @click="deleteResource(r)">
                      <Delete />
                    </el-icon>
                  </div>
                </template>
                <div v-else class="upload-card__empty">尚未上传</div>
              </div>
            </el-card>
          </div>
        </el-form-item>

        <!-- 本地生成分支才需要手动生成；上传规划表分支上传后自动解析总卷量 -->
        <el-form-item v-if="form.plan_source === 'ocr'" label="生成规划表">
          <el-button type="primary" :loading="generating" @click="generatePlan(true)">
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
/* 图标放大到 44px 后，连接线需重新对齐到圆圈垂直中心（22px），线高 2px 故 top=21px */
.wizard-steps :deep(.el-step__line) {
  top: 21px;
}
.wizard-steps :deep(.el-step__title) {
  font-size: 18px;
  font-weight: 600;
}
.wizard-steps :deep(.el-step__description) {
  font-size: 14px;
}

/* ===== 资料上传卡片 ===== */
/* 卡片区脱离表单 920px 限制，占满可用宽度，卡片等分排布 */
.upload-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  width: 100%;
}
.upload-card {
  flex: 1 1 220px;
  min-width: 200px;
  max-width: 320px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.upload-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.12);
}
.upload-card :deep(.el-card__body) {
  padding: 14px;
}
.upload-card__title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.upload-card__name {
  display: flex;
  align-items: center;
  gap: 6px;
}
.upload-card__title strong {
  font-size: 14px;
}
.upload-card__hint {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}
.upload-card :deep(.el-upload),
.upload-card :deep(.el-upload-dragger) {
  width: 100%;
}
.upload-card :deep(.el-upload-dragger) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px 8px;
  border-radius: 8px;
  border-style: dashed;
  background: var(--el-fill-color-lighter);
  transition: background 0.2s, border-color 0.2s;
}
.upload-card :deep(.el-upload-dragger:hover) {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}
.upload-card :deep(.el-icon--upload) {
  font-size: 34px;
  margin-bottom: 8px;
  color: var(--el-color-primary-light-3);
}
.upload-card :deep(.el-upload__text) {
  font-size: 12px;
  white-space: nowrap;
  line-height: 1.2;
}
.upload-card__files {
  margin-top: 12px;
}
.upload-card__empty {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  text-align: center;
}
.upload-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--el-color-success-light-9);
  border: 1px solid var(--el-color-success-light-7);
  margin-bottom: 6px;
}
.upload-file__icon {
  color: var(--el-color-success);
  flex-shrink: 0;
}
.upload-file__name {
  flex: 1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-file__del {
  color: var(--el-color-danger);
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.2s;
}
.upload-file__del:hover {
  opacity: 0.6;
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
