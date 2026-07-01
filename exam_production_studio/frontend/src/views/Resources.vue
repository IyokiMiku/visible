<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '../services/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string
const resources = ref<any[]>([])
const project = ref<any>(null)
const notFound = ref(false)
const uploadUrl = api.uploadResourceUrl(id)

// 各资源类型：接受的扩展名 + 中文提示 + 是否必填。与后端 ALLOWED_EXTS 保持一致。
interface KindDef {
  key: string
  exts: string[]
  hint: string
  required: boolean
}
const DOC_KINDS: KindDef[] = [
  { key: '考纲', exts: ['.pdf', '.doc', '.docx'], hint: 'PDF 或 Word，可添加多份', required: true },
  { key: '教材', exts: ['.pdf', '.doc', '.docx'], hint: 'PDF 或 Word，可选、可多份', required: false },
  { key: '真题', exts: ['.pdf', '.doc', '.docx'], hint: 'PDF 或 Word，可选、可多份', required: false },
]
const TEMPLATE_EXTS = ['.doc', '.docx']
const PLAN_EXTS = ['.xlsx', '.xls']

const STATUS_ZH: Record<string, string> = {
  imported: '已导入',
  pending: '待处理',
  failed: '导入失败',
}
function statusZh(s: string): string {
  return STATUS_ZH[s] || s
}

function accept(exts: string[]): string {
  return exts.join(',')
}

function makeBeforeUpload(exts: string[]) {
  return (file: File): boolean => {
    const name = (file.name || '').toLowerCase()
    const okType = exts.some((e) => name.endsWith(e))
    if (!okType) {
      ElMessage.error(`仅支持 ${exts.join('、')} 格式，请重新选择`)
      return false
    }
    return true
  }
}

// ---- 上传进度反馈 ----
// 以 el-upload 内部文件 uid 为键，记录上传中的文件与百分比
const uploads = ref<Record<string, { name: string; percent: number }>>({})
const uploadingCount = computed(() => Object.keys(uploads.value).length)

function onProgress(evt: any, file: any) {
  uploads.value[String(file.uid)] = { name: file.name, percent: Math.round(evt?.percent || 0) }
}
function onSuccess(resp: any, file: any) {
  if (file?.uid != null) delete uploads.value[String(file.uid)]
  if (resp && typeof resp === 'object' && 'code' in resp && resp.code !== 0) {
    ElMessage.error(resp.message || '上传失败')
    return
  }
  ElMessage.success('上传成功')
  load()
}
function onError(_err: any, file: any) {
  if (file?.uid != null) delete uploads.value[String(file.uid)]
  ElMessage.error('上传失败，请检查文件或网络')
}

async function removeFile(rid: string, filename: string) {
  try {
    await ElMessageBox.confirm(`确认删除「${filename}」？`, '提示', { type: 'warning' })
  } catch {
    return // 用户取消
  }
  try {
    await api.deleteResource(id, rid)
    ElMessage.success('已删除')
    load()
  } catch {
    /* 错误已由全局拦截器提示 */
  }
}

// 模板来源：默认使用系统内置模板 / 上传自定义（本地状态，刷新后按“是否已传自定义模板”初始化）
const templateMode = ref<'default' | 'upload'>('default')
// 规划表来源：与项目 plan_source 联动（ocr=默认使用生成的，upload=上传）
const planMode = computed<'default' | 'upload'>({
  get: () => (project.value?.plan_source === 'upload' ? 'upload' : 'default'),
  set: (v) => setPlanSource(v === 'upload' ? 'upload' : 'ocr'),
})

async function setPlanSource(src: string) {
  const p = project.value
  if (!p || p.plan_source === src) return
  try {
    await api.updateProject(id, {
      name: p.name,
      paper_type: p.paper_type,
      province: p.province,
      exam_category: p.exam_category,
      course: p.course,
      textbook: p.textbook,
      edition: p.edition,
      exam_type_name: p.exam_type_name,
      paper_range: p.paper_range,
      plan_source: src,
      volume_config: p.volume_config,
      output_versions: p.output_versions,
      ai_options: p.ai_options,
    })
    p.plan_source = src
    ElMessage.success(src === 'upload' ? '规划表已设为「上传 xlsx」' : '规划表已设为「使用生成的」')
  } catch {
    /* 错误已由全局拦截器提示 */
  }
}

function filesOf(kind: string) {
  return resources.value.filter((r) => r.kind === kind)
}

// 必填校验：考纲必填；规划表若选“上传”则必须有 xlsx（选“默认生成”时由考纲生成，无需上传）
function missingRequired(): string[] {
  const miss: string[] = []
  if (!filesOf('考纲').length) miss.push('考纲')
  if (planMode.value === 'upload' && !filesOf('规划表').length) miss.push('规划表（xlsx）')
  return miss
}
const missing = computed(() => missingRequired())

function goFlow() {
  const miss = missingRequired()
  if (miss.length) {
    ElMessage.warning(`请先完成必填项：${miss.join('、')}`)
    return
  }
  router.push(`/projects/${id}/flow`)
}

// 首次加载后按已有文件初始化模板模式（避免刷新后自定义模板状态丢失）
let templateInit = false
async function load() {
  resources.value = await api.listResources(id)
  if (!templateInit) {
    templateInit = true
    if (filesOf('模板').length) templateMode.value = 'upload'
  }
}
async function loadProject() {
  try {
    project.value = await api.getProject(id)
  } catch {
    notFound.value = true
  }
}
onMounted(() => {
  loadProject()
  load()
})
</script>

<template>
  <el-result
    v-if="notFound"
    icon="warning"
    title="项目不存在"
    sub-title="该项目可能已被删除，或链接有误。"
  >
    <template #extra>
      <el-button type="primary" @click="router.push('/projects')">返回项目列表</el-button>
    </template>
  </el-result>

  <el-card v-else>
    <template #header>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span>资源导入</span>
        <el-button type="primary" @click="goFlow">进入流程执行</el-button>
      </div>
    </template>

    <el-alert
      v-if="missing.length"
      type="warning"
      :closable="false"
      show-icon
      :title="`还需完成必填项：${missing.join('、')}，否则无法进入流程执行`"
      style="margin-bottom: 16px"
    />
    <el-alert
      v-else
      type="success"
      :closable="false"
      show-icon
      title="必填资源已就绪，可进入流程执行。带 * 为必填；教材、真题为可选。"
      style="margin-bottom: 16px"
    />

    <!-- 上传进度 -->
    <div v-if="uploadingCount" class="uploading-box">
      <div class="uploading-title">上传中（{{ uploadingCount }}）…</div>
      <div v-for="(u, uid) in uploads" :key="uid" class="uploading-row">
        <span class="fname" :title="u.name">{{ u.name }}</span>
        <el-progress :percentage="u.percent" :stroke-width="10" style="flex: 1; min-width: 120px" />
      </div>
    </div>

    <div class="kind-grid">
      <!-- 文档类：考纲(必填) / 教材(可选) / 真题(可选) -->
      <el-card v-for="k in DOC_KINDS" :key="k.key" shadow="never" class="kind-card">
        <div class="kind-title">
          {{ k.key }}
          <span v-if="k.required" class="req">*</span>
          <el-tag v-else size="small" type="info" effect="plain" round>可选</el-tag>
        </div>
        <div class="kind-hint">支持格式：{{ k.hint }}</div>
        <el-upload
          drag
          multiple
          :action="uploadUrl"
          :data="{ kind: k.key }"
          name="file"
          :accept="accept(k.exts)"
          :before-upload="makeBeforeUpload(k.exts)"
          :on-progress="onProgress"
          :on-success="onSuccess"
          :on-error="onError"
          :show-file-list="false"
        >
          <el-icon class="up-icon"><UploadFilled /></el-icon>
          <div class="up-text">拖拽文件到此，或<em>点击选择</em></div>
        </el-upload>
        <div v-if="filesOf(k.key).length" class="kind-files">
          <div v-for="f in filesOf(k.key)" :key="f.id" class="kind-file">
            <span class="fname" :title="f.filename">{{ f.filename }}</span>
            <span class="file-ops">
              <el-tag size="small" type="success">{{ statusZh(f.status) }}</el-tag>
              <el-button size="small" type="danger" link @click="removeFile(f.id, f.filename)">删除</el-button>
            </span>
          </div>
        </div>
      </el-card>

      <!-- 模板：默认 / 上传自定义（可选） -->
      <el-card shadow="never" class="kind-card">
        <div class="kind-title">模板 <el-tag size="small" type="info" effect="plain" round>可选</el-tag></div>
        <el-radio-group v-model="templateMode" size="small" style="margin-bottom: 10px">
          <el-radio-button value="default">使用默认模板</el-radio-button>
          <el-radio-button value="upload">上传自定义</el-radio-button>
        </el-radio-group>
        <template v-if="templateMode === 'default'">
          <div class="kind-note">将使用系统内置排版模板，无需上传。</div>
          <div v-if="filesOf('模板').length" class="kind-warn">
            已上传的自定义模板在“使用默认模板”下不会生效，如需启用请切到“上传自定义”。
          </div>
        </template>
        <template v-else>
          <div class="kind-hint">支持格式：Word 文档（.doc/.docx）</div>
          <el-upload
            drag
            :action="uploadUrl"
            :data="{ kind: '模板' }"
            name="file"
            :accept="accept(TEMPLATE_EXTS)"
            :before-upload="makeBeforeUpload(TEMPLATE_EXTS)"
            :on-progress="onProgress"
            :on-success="onSuccess"
            :on-error="onError"
            :show-file-list="false"
          >
            <el-icon class="up-icon"><UploadFilled /></el-icon>
            <div class="up-text">拖拽模板到此，或<em>点击选择</em></div>
          </el-upload>
          <div v-if="filesOf('模板').length" class="kind-files">
            <div v-for="f in filesOf('模板')" :key="f.id" class="kind-file">
              <span class="fname" :title="f.filename">{{ f.filename }}</span>
              <span class="file-ops">
                <el-tag size="small" type="success">{{ statusZh(f.status) }}</el-tag>
                <el-button size="small" type="danger" link @click="removeFile(f.id, f.filename)">删除</el-button>
              </span>
            </div>
          </div>
        </template>
      </el-card>

      <!-- 规划表：默认使用生成的 / 上传（必填：二选一满足即可） -->
      <el-card shadow="never" class="kind-card">
        <div class="kind-title">规划表 <span class="req">*</span></div>
        <el-radio-group v-model="planMode" size="small" style="margin-bottom: 10px">
          <el-radio-button value="default">默认使用生成的</el-radio-button>
          <el-radio-button value="upload">上传规划表</el-radio-button>
        </el-radio-group>
        <template v-if="planMode === 'default'">
          <div class="kind-note">
            将由系统按<strong>考纲</strong>自动生成规划表（本地 OCR 扫描/合成），无需上传——因此此时考纲为必填。
          </div>
          <div v-if="filesOf('规划表').length" class="kind-warn">
            已上传的规划表在“默认使用生成的”下不会被使用，如需使用请切到“上传规划表”。
          </div>
        </template>
        <template v-else>
          <div class="kind-hint">支持格式：Excel 表格（.xlsx/.xls），必须上传</div>
          <el-upload
            drag
            :action="uploadUrl"
            :data="{ kind: '规划表' }"
            name="file"
            :accept="accept(PLAN_EXTS)"
            :before-upload="makeBeforeUpload(PLAN_EXTS)"
            :on-progress="onProgress"
            :on-success="onSuccess"
            :on-error="onError"
            :show-file-list="false"
          >
            <el-icon class="up-icon"><UploadFilled /></el-icon>
            <div class="up-text">拖拽规划表到此，或<em>点击选择</em></div>
          </el-upload>
          <div v-if="filesOf('规划表').length" class="kind-files">
            <div v-for="f in filesOf('规划表')" :key="f.id" class="kind-file">
              <span class="fname" :title="f.filename">{{ f.filename }}</span>
              <span class="file-ops">
                <el-tag size="small" type="success">{{ statusZh(f.status) }}</el-tag>
                <el-button size="small" type="danger" link @click="removeFile(f.id, f.filename)">删除</el-button>
              </span>
            </div>
          </div>
        </template>
      </el-card>
    </div>
  </el-card>
</template>

<style scoped>
.kind-grid {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.kind-card {
  width: 260px;
}
.kind-title {
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.kind-title .req {
  color: var(--el-color-danger);
  font-weight: 700;
}
.kind-hint {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}
.kind-note {
  color: #67c23a;
  font-size: 12px;
  background: #f0f9eb;
  border-radius: 4px;
  padding: 10px;
  line-height: 1.5;
}
.kind-warn {
  margin-top: 8px;
  color: #e6a23c;
  font-size: 12px;
  background: #fdf6ec;
  border-radius: 4px;
  padding: 8px 10px;
  line-height: 1.5;
}
.uploading-box {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px dashed var(--el-color-primary);
  border-radius: 6px;
  background: #f4f8ff;
}
.uploading-title {
  font-size: 13px;
  color: var(--el-color-primary);
  margin-bottom: 6px;
}
.uploading-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 3px 0;
}
.uploading-row .fname {
  width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.up-icon {
  font-size: 32px;
  color: #c0c4cc;
}
.up-text {
  color: #909399;
  font-size: 13px;
}
.up-text em {
  color: var(--el-color-primary);
  font-style: normal;
}
.kind-files {
  margin-top: 10px;
}
.kind-file {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
}
.kind-file .fname {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kind-file .file-ops {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
:deep(.el-upload-dragger) {
  padding: 16px;
}
</style>
