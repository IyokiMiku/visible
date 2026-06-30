<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../services/api'

const form = reactive<any>({
  llm: { api_key: '', base_url: '', model: '', temperature: '', max_tokens: '' },
  xueke: { cookie: '', app_key: '', sign: '' },
  vision: { enabled: '', model: '', base_url: '', api_key: '' },
  thresholds: { match: '0.85', max_fix_rounds: '2' },
  output: { dir: '' },
})

async function load() {
  const s = await api.getSettings()
  Object.assign(form.llm, s.llm || {})
  Object.assign(form.xueke, s.xueke || {})
  Object.assign(form.vision, s.vision || {})
  Object.assign(form.thresholds, s.thresholds || {})
  Object.assign(form.output, s.output || {})
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

      <el-divider content-position="left">输出目录</el-divider>
      <el-form-item label="成品输出目录">
        <el-input v-model="form.output.dir" placeholder="留空则默认 桌面/生成结果；可填绝对路径，如 D:\\生成结果" />
        <div style="color: #888; font-size: 12px; margin-top: 4px">
          生成完成后，成品与质检报告会自动归档到 此目录/卷类/省份简称 考类/教材或课程/
        </div>
      </el-form-item>

      <el-form-item><el-button type="primary" @click="save">保存</el-button></el-form-item>
    </el-form>
  </el-card>
</template>
