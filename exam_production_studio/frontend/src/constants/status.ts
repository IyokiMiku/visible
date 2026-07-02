// 项目状态（projects.status）公共字典：项目列表页与流程页共用同一套术语。
// 后端在 runner.py 中对项目状态与运行状态同步写入相同的值，因此两页显示必须一致。
// 注意：卷级状态（papers.status）是另一维度，见 Flow.vue 的 PAPER_STATUS_LABEL，不在此处。

export type ProjectStatus =
  | 'draft'
  | 'ready'
  | 'running'
  | 'review'
  | 'paused'
  | 'blocked'
  | 'done'
  | 'failed'

export const PROJECT_STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  ready: '就绪',
  running: '生成中',
  review: '待人工确认',
  paused: '已暂停',
  blocked: '已阻塞',
  done: '已完成',
  failed: '失败',
}

export const PROJECT_STATUS_TYPE: Record<string, string> = {
  draft: 'info',
  ready: 'info',
  running: 'warning',
  review: 'warning',
  paused: 'info',
  blocked: 'warning',
  done: 'success',
  failed: 'danger',
}
