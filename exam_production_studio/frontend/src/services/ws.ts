export type WsHandler = (event: any) => void

export function connectFlowWs(projectId: string, onEvent: WsHandler): () => void {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${proto}://${location.host}/ws/projects/${projectId}`
  let ws: WebSocket | null = new WebSocket(url)
  let pingTimer: number | undefined
  let closed = false

  ws.onopen = () => {
    pingTimer = window.setInterval(() => ws?.readyState === 1 && ws.send('ping'), 15000)
  }
  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data))
    } catch {
      /* ignore */
    }
  }
  ws.onclose = () => {
    if (pingTimer) window.clearInterval(pingTimer)
  }

  return () => {
    closed = true
    if (pingTimer) window.clearInterval(pingTimer)
    ws?.close()
    ws = null
    void closed
  }
}
