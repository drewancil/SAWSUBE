/// <reference lib="dom" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { wsClient } from './ws'

class MockWebSocket {
  static OPEN = 1
  static CONNECTING = 0
  static CLOSED = 3
  static instances: MockWebSocket[] = []
  readyState = MockWebSocket.CONNECTING
  onopen: any = null
  onclose: any = null
  onerror: any = null
  onmessage: any = null
  url: string
  closed = false
  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }
  send(_: string) { /* noop */ }
  close() {
    this.closed = true
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({})
  }
  triggerOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.({})
  }
  triggerMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

describe('wsClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket as any)
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:1234' },
      writable: true,
    })
    wsClient.close()
  })
  afterEach(() => {
    wsClient.close()
    vi.useRealTimers()
  })

  it('connect opens a single websocket', () => {
    wsClient.connect()
    expect(MockWebSocket.instances.length).toBe(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost:1234/ws')
  })

  it('does not double-connect when called twice (StrictMode safe)', () => {
    wsClient.connect()
    wsClient.connect()
    expect(MockWebSocket.instances.length).toBe(1)
  })

  it('routes messages to listeners', () => {
    const handler = vi.fn()
    const off = wsClient.on(handler)
    wsClient.connect()
    MockWebSocket.instances[0].triggerOpen()
    MockWebSocket.instances[0].triggerMessage({ type: 'hello', n: 1 })
    expect(handler).toHaveBeenCalledWith({ type: 'hello', n: 1 })
    off()
    MockWebSocket.instances[0].triggerMessage({ type: 'after-off' })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('on() returns a void cleanup function (not boolean)', () => {
    const off = wsClient.on(() => {})
    const r = off()
    expect(r).toBeUndefined()
  })

  it('explicit close prevents reconnect', () => {
    vi.useFakeTimers()
    wsClient.connect()
    MockWebSocket.instances[0].triggerOpen()
    wsClient.close()
    vi.advanceTimersByTime(60_000)
    expect(MockWebSocket.instances.length).toBe(1)  // no new sockets
  })

  it('reconnects after unexpected close with backoff', () => {
    vi.useFakeTimers()
    wsClient.connect()
    MockWebSocket.instances[0].triggerOpen()
    // Server-side close (not via wsClient.close)
    MockWebSocket.instances[0].onclose?.({})
    vi.advanceTimersByTime(2000)
    expect(MockWebSocket.instances.length).toBe(2)
  })
})
