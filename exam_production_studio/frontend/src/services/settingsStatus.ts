import { reactive } from 'vue'
import { api } from './api'

export interface SettingsIssue {
  group: string
  field?: string | null
  message: string
  runtime?: boolean
}

export const settingsStatus = reactive<{ ok: boolean; issues: SettingsIssue[]; loaded: boolean }>({
  ok: true,
  issues: [],
  loaded: false,
})

export async function refreshSettingsStatus() {
  try {
    const r = await api.checkSettings()
    settingsStatus.ok = !!r?.ok
    settingsStatus.issues = Array.isArray(r?.issues) ? r.issues : []
  } catch {
    // 自检接口异常时不误报红点
  } finally {
    settingsStatus.loaded = true
  }
}
