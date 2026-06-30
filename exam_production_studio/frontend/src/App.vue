<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const currentId = computed(() => (route.params.id as string) || '')

function newWithType(t: string) {
  router.push({ path: '/projects/new', query: { type: t } })
}
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
            <el-menu-item index="t-yikeyilian" @click="newWithType('yikeyilian')">一课一练</el-menu-item>
            <el-menu-item index="t-kaogang_100" @click="newWithType('kaogang_100')">考纲百套卷</el-menu-item>
            <el-menu-item index="t-shuangxi" @click="newWithType('shuangxi')">考点双析卷</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="工作区">
            <el-menu-item index="/projects">项目列表</el-menu-item>
            <el-menu-item index="/projects/new">项目创建</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group v-if="currentId" title="当前项目">
            <el-menu-item :index="`/projects/${currentId}/resources`">资源导入</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/flow`">流程执行</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/reviews`">待确认事项</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/quality`">质量摘要</el-menu-item>
            <el-menu-item :index="`/projects/${currentId}/artifacts`">输出归档</el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="系统">
            <el-menu-item index="/settings">全局设置</el-menu-item>
          </el-menu-item-group>
        </el-menu>
      </el-aside>
      <el-main style="background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
