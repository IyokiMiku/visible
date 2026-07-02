<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import GlobalSettingsForm from './components/GlobalSettingsForm.vue'
import { settingsStatus, refreshSettingsStatus } from './services/settingsStatus'

const route = useRoute()
const currentId = computed(() => (route.params.id as string) || '')

const showFirstRun = ref(false)

async function init() {
  await refreshSettingsStatus()
  // 首次运行：仅当缺「必填静态项」时强制弹窗（运行时错误只点红点、不强制弹窗）
  const hasStaticMissing = settingsStatus.issues.some((i) => !i.runtime)
  if (hasStaticMissing) showFirstRun.value = true
}

function onSaved() {
  showFirstRun.value = false
  refreshSettingsStatus()
}

onMounted(init)
// 切换路由时刷新一次，及时反映运行时配置错误（如 Cookie 失效）
watch(() => route.path, () => refreshSettingsStatus())
</script>

<template>
  <el-container style="height: 100vh">
    <el-header
      style="display: flex; align-items: center; background: #1f2d3d; color: #fff; gap: 12px"
    >
      <strong style="font-size: 18px">出卷集成工作台</strong>
      <span style="opacity: 0.6; font-size: 13px">Exam Production Studio</span>
    </el-header>
    <el-container>
      <el-aside width="220px" style="border-right: 1px solid #eee; overflow: auto">
        <el-menu :default-active="route.path" router>
          <el-menu-item-group title="产品系列">
            <el-menu-item index="/paper-types/yikeyilian/config">一课一练</el-menu-item>
            <el-menu-item index="/paper-types/kaogang_100/config">考纲百套卷</el-menu-item>
            <el-menu-item index="/paper-types/shuangxi/config">考点双析卷</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="工作区">
            <el-menu-item index="/projects">项目列表</el-menu-item>
            <el-menu-item index="/projects/new">项目创建</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group v-if="currentId" title="当前项目">
            <el-menu-item :index="`/projects/${currentId}/flow`">流程执行</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/gates`">规划确认闸门</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/reviews`">待确认事项</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/content-review`">内容审阅</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/quality`">质量摘要</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/artifacts`">输出归档</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/files`">中间文件</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="系统">
            <el-menu-item index="/settings">
              <el-badge is-dot :hidden="settingsStatus.ok" type="danger">全局设置</el-badge>
            </el-menu-item>
          </el-menu-item-group>
        </el-menu>
      </el-aside>
      <el-main style="background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>

    <el-dialog
      v-model="showFirstRun"
      title="首次使用 · 请完成全局设置"
      width="760px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      align-center
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="欢迎使用出卷集成工作台"
        description="首次使用请先完成大模型与学科网的必填配置，填写完整并保存后方可开始使用。"
        style="margin-bottom: 12px"
      />
      <GlobalSettingsForm @saved="onSaved" />
    </el-dialog>
  </el-container>
</template>
