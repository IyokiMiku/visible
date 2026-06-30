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

  getSettings: () => http.get<any, any>('/settings'),
  putSettings: (body: any) => http.put('/settings', body),

  getPaperType: (type: string) => http.get<any, any>(`/paper-types/${type}`),
  putEditorialNote: (type: string, content: string) =>
    http.put(`/paper-types/${type}/editorial-note`, { content }),
  putSpec: (type: string, content: string) =>
    http.put(`/paper-types/${type}/spec`, { content }),
  previewPaperType: (type: string, editorial_note: string) =>
    http.post<Blob, Blob>(`/paper-types/${type}/preview`, { editorial_note }, { responseType: 'blob' }),
}

export default http
