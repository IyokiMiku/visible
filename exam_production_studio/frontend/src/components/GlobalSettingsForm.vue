<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { api } from '../services/api'
import { settingsStatus, refreshSettingsStatus } from '../services/settingsStatus'

const emit = defineEmits<{ (e: 'saved'): void }>()

const formRef = ref<FormInstance>()
const saving = ref(false)

const form = reactive<any>({
  llm: { api_key: '', base_url: '', model: '', temperature: '0.2', max_tokens: '' },
  xueke: { cookie: '', app_key: '', sign: '' },
  vision: { enabled: '', model: '', base_url: '', api_key: '' },
  thresholds: { match: '0.85', max_fix_rounds: '2' },
  output: { dir: '' },
})

const validateTemperature = (_rule: any, value: any, callback: any) => {
  const s = String(value ?? '').trim()
  if (!s) {
    callback(new Error('请填写温度'))
    return
  }
  const n = Number(s)
  if (Number.isNaN(n)) {
    callback(new Error('温度必须是数字'))
    return
  }
  if (n < 0.01 || n > 0.3) {
    callback(new Error('温度取值范围为 0.01 ~ 0.3'))
    return
  }
  callback()
}

const rules: FormRules = {
  'llm.api_key': [{ required: true, message: '请填写大模型 API 密钥', trigger: 'blur' }],
  'llm.base_url': [{ required: true, message: '请填写大模型接口地址', trigger: 'blur' }],
  'llm.model': [{ required: true, message: '请填写大模型名称', trigger: 'blur' }],
  'llm.temperature': [{ validator: validateTemperature, trigger: 'blur' }],
  'xueke.cookie': [{ required: true, message: '请填写学科网 Cookie', trigger: 'blur' }],
}

const cookieBusy = ref(false)
const loginPolling = ref(false)
let loginTimer: number | null = null

async function autoReadCookie() {
  cookieBusy.value = true
  try {
    const r = await api.xkAutoReadCookie()
    if (r?.ok) {
      ElMessage.success(r.message || '已读取学科网 Cookie')
      await load()
    } else {
      ElMessage.warning(r?.message || '未能自动读取，请改用「登录学科网」')
    }
  } finally {
    cookieBusy.value = false
  }
}

function stopLoginPoll() {
  if (loginTimer !== null) {
    window.clearInterval(loginTimer)
    loginTimer = null
  }
  loginPolling.value = false
}

async function startLogin() {
  const r = await api.xkLoginStart()
  if (r?.state === 'failed') {
    ElMessage.error(r.message || '无法打开登录窗口')
    return
  }
  ElMessage.info(r?.message || '已打开登录窗口，请在浏览器中登录')
  loginPolling.value = true
  loginTimer = window.setInterval(async () => {
    const st = await api.xkLoginStatus()
    if (st?.state === 'success') {
      stopLoginPoll()
      ElMessage.success(st.message || '登录成功，已保存 Cookie')
      await load()
    } else if (['failed', 'timeout', 'cancelled'].includes(st?.state)) {
      stopLoginPoll()
      ElMessage.warning(st.message || '登录未完成')
    }
  }, 2000)
}

async function confirmLogin() {
  const r = await api.xkLoginConfirm()
  ElMessage.info(r?.message || '正在读取登录信息……')
}

async function load() {
  const s = await api.getSettings()
  Object.assign(form.llm, s.llm || {})
  Object.assign(form.xueke, s.xueke || {})
  Object.assign(form.vision, s.vision || {})
  Object.assign(form.thresholds, s.thresholds || {})
  Object.assign(form.output, s.output || {})
  if (!String(form.llm.temperature ?? '').trim()) form.llm.temperature = '0.2'
  refreshSettingsStatus()
}

async function save() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请先补全必填项后再保存')
    return
  }
  saving.value = true
  try {
    await api.putSettings(form)
    ElMessage.success('已保存')
    await load()
    await refreshSettingsStatus()
    emit('saved')
  } finally {
    saving.value = false
  }
}

onMounted(load)
onUnmounted(stopLoginPoll)

defineExpose({ load, save })
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
    <el-alert
      v-if="!settingsStatus.ok && settingsStatus.issues.length"
      type="error"
      :closable="false"
      show-icon
      title="以下设置需要处理"
      style="margin-bottom: 12px"
    >
      <ul style="margin: 4px 0 0; padding-left: 18px">
        <li v-for="(it, i) in settingsStatus.issues" :key="i">{{ it.message }}</li>
      </ul>
    </el-alert>

    <el-divider content-position="left">大模型（LLM）</el-divider>
    <el-form-item label="API 密钥" prop="llm.api_key">
      <el-input v-model="form.llm.api_key" type="password" show-password placeholder="留空或 ***已配置*** 表示不修改" />
    </el-form-item>
    <el-form-item label="接口地址" prop="llm.base_url">
      <el-input v-model="form.llm.base_url" placeholder="如 https://api.openai.com/v1" />
    </el-form-item>
    <el-form-item label="模型名称" prop="llm.model">
      <el-input v-model="form.llm.model" placeholder="如 gpt-4o" />
    </el-form-item>
    <el-form-item label="温度" prop="llm.temperature">
      <el-input v-model="form.llm.temperature" placeholder="取值范围 0.01 ~ 0.3" />
      <div style="color: #888; font-size: 12px; margin-top: 4px">值越低越稳定，出卷建议 0.01 ~ 0.3。</div>
    </el-form-item>
    <el-form-item label="最大 Token 数" prop="llm.max_tokens">
      <el-input v-model="form.llm.max_tokens" placeholder="可留空使用默认" />
    </el-form-item>

    <el-divider content-position="left">学科网</el-divider>
    <el-form-item label="Cookie" prop="xueke.cookie">
      <el-input v-model="form.xueke.cookie" type="textarea" :rows="3" placeholder="可点下方按钮自动获取，或手动粘贴" />
      <div style="margin-top: 6px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap">
        <el-button size="small" :loading="cookieBusy" @click="autoReadCookie">一键读取（浏览器）</el-button>
        <el-button size="small" type="primary" :disabled="loginPolling" @click="startLogin">登录学科网</el-button>
        <el-button v-if="loginPolling" size="small" type="success" @click="confirmLogin">我已登录完成</el-button>
        <span v-if="loginPolling" style="color: #e6a23c; font-size: 12px">请在弹出的浏览器中登录，完成后点「我已登录完成」</span>
      </div>
      <div style="color: #888; font-size: 12px; margin-top: 4px">
        小白推荐「登录学科网」：弹出窗口正常登录即可，无需自己找 Cookie；「一键读取」在浏览器加密限制下可能失败。
      </div>
    </el-form-item>
    <el-form-item label="App Key" prop="xueke.app_key">
      <el-input v-model="form.xueke.app_key" placeholder="选填，留空使用系统默认应用标识" />
    </el-form-item>
    <el-form-item label="签名（Sign）" prop="xueke.sign">
      <el-input v-model="form.xueke.sign" placeholder="选填，留空使用系统默认签名" />
    </el-form-item>

    <el-divider content-position="left">视觉模型（预留）</el-divider>
    <el-form-item label="启用"><el-switch v-model="form.vision.enabled" disabled /></el-form-item>
    <el-form-item label="模型名称"><el-input v-model="form.vision.model" disabled placeholder="后续启用" /></el-form-item>

    <el-divider content-position="left">默认阈值</el-divider>
    <el-form-item label="信度阈值"><el-input v-model="form.thresholds.match" /></el-form-item>
    <el-form-item label="修复轮数"><el-input v-model="form.thresholds.max_fix_rounds" /></el-form-item>

    <el-divider content-position="left">输出目录</el-divider>
    <el-form-item label="成品输出目录">
      <el-input v-model="form.output.dir" placeholder="留空则默认 桌面/生成结果；可填绝对路径，如 D:\生成结果" />
      <div style="color: #888; font-size: 12px; margin-top: 4px">
        生成完成后，成品与质检报告会自动归档到 此目录/卷类/省份简称 考类/教材或课程/
      </div>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </el-form-item>
  </el-form>
</template>
