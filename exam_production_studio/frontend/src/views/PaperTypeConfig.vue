<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const route = useRoute()
const paperType = ref<string>((route.params.type as string) || '')

const form = reactive<{ editorial_note: string; spec: string }>({ editorial_note: '', spec: '' })
const displayName = ref('')
const placeholders = ref<Array<{ key: string; desc: string }>>([])

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
    placeholders.value = d.placeholders || []
    await refreshPreview()
  } finally {
    loading.value = false
  }
}

async function refreshPreview() {
  previewing.value = true
  try {
    const blob = await api.previewPaperType(paperType.value, form.editorial_note)
    if (blob && blob.type && blob.type.includes('pdf')) {
      if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = URL.createObjectURL(blob)
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
    ElMessage.success('编写规范已保存（全局生效）')
  } finally {
    savingSpec.value = false
  }
}

watch(
  () => route.params.type,
  (t) => {
    if (t && t !== paperType.value) {
      paperType.value = t as string
      load()
    }
  },
)

onMounted(load)
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
</template>
