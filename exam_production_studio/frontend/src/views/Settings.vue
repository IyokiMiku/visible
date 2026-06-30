<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const form = reactive<any>({
  llm: { api_key: '', base_url: '', model: '', temperature: '', max_tokens: '' },
  xueke: { cookie: '', app_key: '', sign: '' },
  vision: { enabled: '', model: '', base_url: '', api_key: '' },
  thresholds: { match: '0.85', max_fix_rounds: '2' },
})

async function load() {
  const s = await api.getSettings()
  Object.assign(form.llm, s.llm || {})
  Object.assign(form.xueke, s.xueke || {})
  Object.assign(form.vision, s.vision || {})
  Object.assign(form.thresholds, s.thresholds || {})
}
async function save() {
  await api.putSettings(form)
  ElMessage.success('已保存')
  load()
}
onMounted(load)
</script>

<template>
  <el-card style="max-width: 720px">
    <template #header>全局设置</template>
    <el-form label-width="120px">
      <el-divider content-position="left">LLM</el-divider>
      <el-form-item label="api_key"><el-input v-model="form.llm.api_key" type="password" show-password placeholder="留空或 ***已配置*** 表示不修改" /></el-form-item>
      <el-form-item label="base_url"><el-input v-model="form.llm.base_url" /></el-form-item>
      <el-form-item label="model"><el-input v-model="form.llm.model" /></el-form-item>
      <el-form-item label="temperature"><el-input v-model="form.llm.temperature" /></el-form-item>
      <el-form-item label="max_tokens"><el-input v-model="form.llm.max_tokens" /></el-form-item>

      <el-divider content-position="left">学科网</el-divider>
      <el-form-item label="cookie"><el-input v-model="form.xueke.cookie" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="app_key"><el-input v-model="form.xueke.app_key" /></el-form-item>
      <el-form-item label="sign"><el-input v-model="form.xueke.sign" /></el-form-item>

      <el-divider content-position="left">视觉模型（预留）</el-divider>
      <el-form-item label="启用"><el-switch v-model="form.vision.enabled" disabled /></el-form-item>
      <el-form-item label="model"><el-input v-model="form.vision.model" disabled placeholder="后续启用" /></el-form-item>

      <el-divider content-position="left">默认阈值</el-divider>
      <el-form-item label="信度阈值"><el-input v-model="form.thresholds.match" /></el-form-item>
      <el-form-item label="修复轮数"><el-input v-model="form.thresholds.max_fix_rounds" /></el-form-item>

      <el-form-item><el-button type="primary" @click="save">保存</el-button></el-form-item>
    </el-form>
  </el-card>
</template>
