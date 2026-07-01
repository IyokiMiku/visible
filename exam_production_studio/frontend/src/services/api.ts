import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.response.use(
  (resp) => {
    const data = resp.data
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code !== 0) {
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message))
      }
      return data.data
    }
    return data
  },
  (err) => {
    ElMessage.error(err?.response?.data?.message || err.message || '网络错误')
    return Promise.reject(err)
  },
)

export interface Project {
  id: string
  name: string
  paper_type: string
  province: string
  exam_category: string
  course: string
  textbook: string
  edition: string
  exam_type_name: string
  paper_range: string
  plan_source: string
  status: string
  created_at?: string
  volume_config?: any
  output_versions?: string[]
  ai_options?: any
}

export const api = {
  listProjects: () => http.get<Project[], Project[]>('/projects'),
  createProject: (body: any) => http.post<Project, Project>('/projects', body),
  getProject: (id: string) => http.get<Project, Project>(`/projects/${id}`),
  updateProject: (id: string, body: any) => http.put(`/projects/${id}`, body),
  deleteProject: (id: string) => http.delete(`/projects/${id}`),
  namePreview: (id: string) => http.get<any, any>(`/projects/${id}/name-preview`),

  listResources: (id: string) => http.get<any[], any[]>(`/projects/${id}/resources`),
  uploadResourceUrl: (id: string) => `/api/projects/${id}/resources`,

  getPlan: (id: string) => http.get<any, any>(`/projects/${id}/plan`),
  generatePlan: (id: string, plan_source?: string) =>
    http.post<any, any>(`/projects/${id}/plan/generate`, { plan_source }),

  getFlow: (id: string) => http.get<any, any>(`/projects/${id}/flow`),
  start: (id: string) => http.post(`/projects/${id}/flow/start`),
  pause: (id: string) => http.post(`/projects/${id}/flow/pause`),
  resume: (id: string) => http.post(`/projects/${id}/flow/resume`),
  rerun: (id: string, node: string, paper_no?: number) =>
    http.post(`/projects/${id}/flow/rerun`, { node, paper_no }),
  logs: (id: string) => http.get<any[], any[]>(`/projects/${id}/flow/logs`),

  reviews: (id: string, status = 'pending') =>
    http.get<any[], any[]>(`/projects/${id}/reviews`, { params: { status } }),
  confirm: (id: string, rid: string, decision?: any) =>
    http.post(`/projects/${id}/reviews/${rid}/confirm`, { decision }),
  returnReview: (id: string, rid: string) => http.post(`/projects/${id}/reviews/${rid}/return`),

  quality: (id: string) => http.get<any, any>(`/projects/${id}/quality`),
  qcReports: (id: string) => http.get<any[], any[]>(`/projects/${id}/qc/reports`),
  qcReport: (id: string, no: number) => http.get<any, any>(`/projects/${id}/qc/reports/${no}`),

  artifacts: (id: string) => http.get<any, any>(`/projects/${id}/artifacts`),
  downloadUrl: (id: string, path: string) =>
    `/api/projects/${id}/artifacts/download?path=${encodeURIComponent(path)}`,
  zipUrl: (id: string) => `/api/projects/${id}/artifacts/zip`,
  openOutputFolder: (id: string) => http.post<any, any>(`/projects/${id}/artifacts/open`),
  artifactTree: (id: string, base = '04_生成输出') =>
    http.get<any, any>(`/projects/${id}/artifacts/tree`, { params: { base } }),
  previewXlsx: (id: string, path: string) =>
    http.get<any, any>(`/projects/${id}/artifacts/preview-xlsx`, { params: { path } }),

  getSettings: () => http.get<any, any>('/settings'),
  putSettings: (body: any) => http.put('/settings', body),
  checkSettings: () => http.get<any, any>('/settings/check'),
  xkAutoReadCookie: () => http.post<any, any>('/settings/xueke/cookie/auto-read'),
  xkLoginStart: () => http.post<any, any>('/settings/xueke/cookie/login/start'),
  xkLoginConfirm: () => http.post<any, any>('/settings/xueke/cookie/login/confirm'),
  xkLoginCancel: () => http.post<any, any>('/settings/xueke/cookie/login/cancel'),
  xkLoginStatus: () => http.get<any, any>('/settings/xueke/cookie/login/status'),

  // 内容审阅（路线B）
  crPapers: (id: string) => http.get<any[], any[]>(`/projects/${id}/content-review/papers`),
  crPaper: (id: string, no: number) => http.get<any, any>(`/projects/${id}/content-review/${no}`),
  crEditQuestion: (id: string, no: number, num: number, body: any) =>
    http.put(`/projects/${id}/content-review/${no}/question/${num}`, body),
  crReorderOptions: (id: string, no: number, num: number, order: number[]) =>
    http.post(`/projects/${id}/content-review/${no}/question/${num}/reorder-options`, { order }),
  crRegenerate: (id: string, no: number, num: number) =>
    http.post<any, any>(`/projects/${id}/content-review/${no}/question/${num}/regenerate`),
  crConfirm: (id: string, no: number, num: number) =>
    http.post<any, any>(`/projects/${id}/content-review/${no}/question/${num}/confirm`),
  crApprove: (id: string, no: number) =>
    http.post<any, any>(`/projects/${id}/content-review/${no}/approve`),

  getPaperType: (type: string) => http.get<any, any>(`/paper-types/${type}`),
  getQuestionTypes: (type: string, course = '', category = '') =>
    http.get<any, any>(`/paper-types/${type}/question-types`, { params: { course, category } }),
  getTypeLibrary: (type: string) => http.get<any, any>(`/paper-types/${type}/library`),
  saveCustomTypes: (type: string, entry_id: string, types: string[]) =>
    http.put(`/paper-types/${type}/custom-types`, { entry_id, types }),
  putEditorialNote: (type: string, content: string) =>
    http.put(`/paper-types/${type}/editorial-note`, { content }),
  putSpec: (type: string, content: string) =>
    http.put(`/paper-types/${type}/spec`, { content }),
  putFullScore: (type: string, full_score: number) =>
    http.put(`/paper-types/${type}/full-score`, { full_score }),
  loadPaperTypePreview: (type: string) =>
    http.get<Blob, Blob>(`/paper-types/${type}/preview`, { responseType: 'blob' }),
  previewPaperType: (type: string, editorial_note: string) =>
    http.post<Blob, Blob>(`/paper-types/${type}/preview`, { editorial_note }, { responseType: 'blob' }),
}

export default http
