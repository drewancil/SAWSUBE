/// <reference lib="dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { ToastProvider, useToast } from './Toast'
import { wsClient } from '../lib/ws'

let wsHandler: ((m: any) => void) | null = null

beforeEach(() => {
  wsHandler = null
  vi.spyOn(wsClient, 'on').mockImplementation((cb: any) => {
    wsHandler = cb
    return () => { wsHandler = null }
  })
  vi.useFakeTimers()
})

function Pusher() {
  const t = useToast()
  return <button onClick={() => t.push({ type: 'info', text: 'hello' })}>go</button>
}

describe('ToastProvider', () => {
  it('renders pushed toasts and auto-dismisses after 4s', () => {
    render(<ToastProvider><Pusher /></ToastProvider>)
    act(() => { screen.getByText('go').click() })
    expect(screen.getByText('hello')).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(4001) })
    expect(screen.queryByText('hello')).not.toBeInTheDocument()
  })

  it('shows toast for ws image_added', () => {
    render(<ToastProvider><div /></ToastProvider>)
    act(() => { wsHandler?.({ type: 'image_added', filename: 'x.jpg' }) })
    expect(screen.getByText(/Image added: x\.jpg/)).toBeInTheDocument()
  })

  it('dedupes consecutive offline toasts for same TV', () => {
    render(<ToastProvider><div /></ToastProvider>)
    act(() => {
      wsHandler?.({ type: 'tv_status', tv_id: 1, payload: { online: false } })
      wsHandler?.({ type: 'tv_status', tv_id: 1, payload: { online: false } })
      wsHandler?.({ type: 'tv_status', tv_id: 1, payload: { online: false } })
    })
    expect(screen.getAllByText(/TV 1 offline/).length).toBe(1)
  })

  it('re-shows offline after coming back online then offline again', () => {
    render(<ToastProvider><div /></ToastProvider>)
    act(() => {
      wsHandler?.({ type: 'tv_status', tv_id: 2, payload: { online: false } })
    })
    act(() => { vi.advanceTimersByTime(4001) })  // dismiss
    act(() => {
      wsHandler?.({ type: 'tv_status', tv_id: 2, payload: { online: true } })
      wsHandler?.({ type: 'tv_status', tv_id: 2, payload: { online: false } })
    })
    expect(screen.getByText(/TV 2 offline/)).toBeInTheDocument()
  })
})
