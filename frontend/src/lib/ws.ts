type Listener = (msg: any) => void

class WSClient {
  private ws: WebSocket | null = null
  private listeners = new Set<Listener>()
  private retry = 1000
  private connecting = false
  private explicitClose = false

  connect() {
    if (this.connecting || (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING))) {
      return
    }
    this.connecting = true
    this.explicitClose = false
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const host = location.host
    const ws = new WebSocket(`${proto}://${host}/ws`)
    this.ws = ws
    ws.onmessage = (e) => {
      try { this.listeners.forEach((l) => l(JSON.parse(e.data))) } catch { /* ignore */ }
    }
    ws.onopen = () => { this.connecting = false; this.retry = 1000 }
    ws.onerror = () => { /* swallow; close will follow */ }
    ws.onclose = () => {
      this.connecting = false
      this.ws = null
      if (this.explicitClose) return
      setTimeout(() => this.connect(), this.retry)
      this.retry = Math.min(this.retry * 2, 15000)
    }
  }

  close() {
    this.explicitClose = true
    try { this.ws?.close() } catch { /* ignore */ }
    this.ws = null
  }

  on(l: Listener) { this.listeners.add(l); return () => { this.listeners.delete(l) } }
}

export const wsClient = new WSClient()
