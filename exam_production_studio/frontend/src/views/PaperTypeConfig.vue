<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { api } from '../services/api'

const route = useRoute()
const paperType = ref<string>((route.params.type as string) || '')

const form = reactive<{ editorial_note: string; spec: string }>({ editorial_note: '', spec: '' })
const displayName = ref('')
const placeholders = ref<Array<{ key: string; desc: string }>>([])

// 已保存基线：load() / 保存成功后更新，用于「改过才自动保存」的脏检查
const savedNote = ref('')
const savedSpec = ref('')
// 上次生成预览时所用的“编写说明”原文，用于提示“样张与当前编写说明不一致”
const previewedNote = ref('')

const noteDirty = computed(() => form.editorial_note !== savedNote.value)
const specDirty = computed(() => form.spec !== savedSpec.value)
const dirty = computed(() => noteDirty.value || specDirty.value)
// 纯前端字符串比较，无网络/无重新生成，开销可忽略
const previewStale = computed(() => form.editorial_note !== previewedNote.value)

const loading = ref(false)
const savingNote = ref(false)
const savingSpec = ref(false)
const previewing = ref(false)
const previewUrl = ref('')

async function load() {
  loading.value = true
  try {
    const d = await api.getPaperType(paperType.value)
    displayName.value = d.display_name
    form.editorial_note = d.editorial_note || ''
    form.spec = d.spec || ''
    savedNote.value = form.editorial_note
    savedSpec.value = form.spec
    placeholders.value = d.placeholders || []
    await loadPreview()
  } finally {
    loading.value = false
  }
}

async function applyPreviewBlob(blob: Blob | undefined): Promise<boolean> {
  if (blob && blob.type && blob.type.includes('pdf')) {
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(blob)
    return true
  } else if (blob) {
    const text = await blob.text()
    let msg = '预览生成失败'
    try {
      msg = JSON.parse(text).message || msg
    } catch {
      /* keep default */
    }
    ElMessage.error(msg)
  }
  return false
}

// 进入页面时：有样张则直接显示，没有才生成一次（不重复跑 LibreOffice）。
async function loadPreview() {
  previewing.value = true
  try {
    // 已保存内容对应的样张：加载成功即视为“与当前编写说明一致”
    const used = form.editorial_note
    if (await applyPreviewBlob(await api.loadPaperTypePreview(paperType.value))) {
      previewedNote.value = used
    }
  } catch {
    /* interceptor already shows network errors */
  } finally {
    previewing.value = false
  }
}

// 强制重新生成：保存编写说明后 / 手动“刷新预览”时使用。
async function refreshPreview() {
  previewing.value = true
  try {
    const used = form.editorial_note
    if (await applyPreviewBlob(await api.previewPaperType(paperType.value, used))) {
      previewedNote.value = used
    }
  } catch {
    /* interceptor already shows network errors */
  } finally {
    previewing.value = false
  }
}

async function saveNote() {
  savingNote.value = true
  try {
    await api.putEditorialNote(paperType.value, form.editorial_note)
    savedNote.value = form.editorial_note
    ElMessage.success('编写说明已保存（全局生效）')
    await refreshPreview()
  } finally {
    savingNote.value = false
  }
}

async function saveSpec() {
  savingSpec.value = true
  try {
    await api.putSpec(paperType.value, form.spec)
    savedSpec.value = form.spec
    ElMessage.success('编写规范已保存（全局生效）')
  } finally {
    savingSpec.value = false
  }
}

// 离开确认弹窗：有未保存改动时三选一（保存并离开 / 不保存且离开 / 取消）。
const leaveDialogVisible = ref(false)
const leaveSaving = ref(false)
let leaveResolver: ((choice: 'save' | 'discard' | 'cancel') => void) | null = null

function askLeave(): Promise<'save' | 'discard' | 'cancel'> {
  return new Promise((resolve) => {
    leaveResolver = resolve
    leaveDialogVisible.value = true
  })
}

function resolveLeave(choice: 'save' | 'discard' | 'cancel') {
  leaveDialogVisible.value = false
  const r = leaveResolver
  leaveResolver = null
  r?.(choice)
}

// “保存并离开”等价点“保存编写说明”：保存改动并（若编写说明变了）重新生成样张。
async function onLeaveSave() {
  leaveSaving.value = true
  try {
    if (noteDirty.value) {
      await api.putEditorialNote(paperType.value, form.editorial_note)
      savedNote.value = form.editorial_note
      await refreshPreview()
    }
    if (specDirty.value) {
      await api.putSpec(paperType.value, form.spec)
      savedSpec.value = form.spec
    }
    resolveLeave('save')
  } catch {
    /* 拦截器已提示；保存失败则不放行，留在本页 */
    resolveLeave('cancel')
  } finally {
    leaveSaving.value = false
  }
}

// 处理一次“可能带未保存改动”的离开，返回是否放行。
async function guardLeave(): Promise<boolean> {
  if (!dirty.value) return true
  const choice = await askLeave()
  if (choice === 'cancel') return false
  if (choice === 'discard') {
    // 还原为已保存基线，避免残留改动影响 beforeunload 提示
    form.editorial_note = savedNote.value
    form.spec = savedSpec.value
  }
  return true
}

// 切换产品系列（同一路由、仅 type 变化）后，加载新系列配置
watch(
  () => route.params.type,
  (t) => {
    if (t && t !== paperType.value) {
      paperType.value = t as string
      load()
    }
  },
)

// 切换产品系列前（同组件、参数变化）就未保存改动询问用户；取消则中止导航
onBeforeRouteUpdate(async (to, from) => {
  if (to.params.type === from.params.type) return true
  return await guardLeave()
})

// 跳去别的路由（如全局设置、项目列表）前，就未保存改动询问用户
onBeforeRouteLeave(async () => {
  return await guardLeave()
})

// 关闭/刷新标签页：有未保存改动时弹浏览器原生确认框（文案由浏览器决定，无法自定义）
function onBeforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  load()
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
</script>

<template>
  <el-card v-loading="loading">
    <template #header>
      <span>{{ displayName || paperType }} · 专属配置</span>
    </template>

    <el-row :gutter="16">
      <el-col :span="11">
        <el-divider content-position="left">首部编写说明（DOCX 蓝框）</el-divider>
        <el-input
          v-model="form.editorial_note"
          type="textarea"
          :rows="6"
          placeholder="支持占位符，按回车分段"
        />
        <div style="margin-top: 6px; color: #888; font-size: 12px">
          可用占位符：
          <el-tag
            v-for="p in placeholders"
            :key="p.key"
            size="small"
            style="margin: 2px 4px 2px 0"
            :title="p.desc"
          >{{ p.key }}</el-tag>
        </div>
        <div style="margin-top: 10px">
          <el-button type="primary" :loading="savingNote" @click="saveNote">保存编写说明</el-button>
          <el-button :loading="previewing" @click="refreshPreview">刷新预览</el-button>
        </div>
        <div
          v-if="previewUrl && previewStale"
          style="margin-top: 6px; color: var(--el-color-warning); font-size: 12px"
        >
          ⚠ 编写说明已改动，右侧样张为旧版，点「刷新预览」或「保存编写说明」更新
        </div>

        <el-divider content-position="left">编写规范.md（供 AI 出题）</el-divider>
        <el-input
          v-model="form.spec"
          type="textarea"
          :rows="16"
          input-style="font-family: Consolas, monospace; font-size: 12px"
        />
        <div style="margin-top: 10px">
          <el-button type="primary" :loading="savingSpec" @click="saveSpec">保存编写规范</el-button>
        </div>
      </el-col>

      <el-col :span="13">
        <el-divider content-position="left">模板样张预览（PDF）</el-divider>
        <div v-loading="previewing" style="min-height: 640px">
          <iframe
            v-if="previewUrl"
            :src="previewUrl"
            style="width: 100%; height: 640px; border: 1px solid #eee"
          ></iframe>
          <el-empty v-else description="暂无预览（点击“刷新预览”生成；需本机安装 LibreOffice）" />
        </div>
      </el-col>
    </el-row>
  </el-card>

  <el-dialog
    v-model="leaveDialogVisible"
    title="未保存的改动"
    width="440px"
    align-center
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="!leaveSaving"
    @close="resolveLeave('cancel')"
  >
    <div class="leave-body">
      <el-icon class="leave-icon"><WarningFilled /></el-icon>
      <span>您现在的改动尚未保存，确认离开吗？</span>
    </div>
    <template #footer>
      <div class="leave-footer">
        <el-button :disabled="leaveSaving" @click="resolveLeave('cancel')">取消</el-button>
        <el-button :disabled="leaveSaving" @click="resolveLeave('discard')">不保存且离开</el-button>
        <el-button type="primary" :loading="leaveSaving" @click="onLeaveSave">保存并离开</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.leave-body {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
}
.leave-icon {
  font-size: 22px;
  color: var(--el-color-warning);
  flex-shrink: 0;
}
.leave-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
