import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', name: 'projects', component: () => import('../views/ProjectList.vue') },
  { path: '/projects/new', name: 'project-new', component: () => import('../views/ProjectNew.vue') },
  { path: '/paper-types/:type/config', name: 'paper-type-config', component: () => import('../views/PaperTypeConfig.vue') },
  { path: '/projects/:id/resources', name: 'resources', component: () => import('../views/Resources.vue') },
  { path: '/projects/:id/flow', name: 'flow', component: () => import('../views/Flow.vue') },
  { path: '/projects/:id/reviews', name: 'reviews', component: () => import('../views/Reviews.vue') },
  { path: '/projects/:id/quality', name: 'quality', component: () => import('../views/Quality.vue') },
  { path: '/projects/:id/artifacts', name: 'artifacts', component: () => import('../views/Artifacts.vue') },
  { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue') },
]

export default createRouter({ history: createWebHashHistory(), routes })
