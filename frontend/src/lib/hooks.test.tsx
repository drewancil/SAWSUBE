/// <reference lib="dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWS, useToggleTheme } from './hooks'
import { wsClient } from './ws'

describe('useWS', () => {
  beforeEach(() => {
    // Replace wsClient.on with controllable spy
    vi.spyOn(wsClient, 'on').mockImplementation((cb: any) => {
      ;(wsClient as any)._cb = cb
      return () => { (wsClient as any)._cb = null }
    })
  })

  it('subscribes once even if handler identity changes', () => {
    const onSpy = wsClient.on as any
    const { rerender } = renderHook(({ h }) => useWS(h), {
      initialProps: { h: () => {} },
    })
    rerender({ h: () => {} })
    rerender({ h: () => {} })
    expect(onSpy).toHaveBeenCalledTimes(1)
  })

  it('routes messages through latest handler', () => {
    const h1 = vi.fn()
    const h2 = vi.fn()
    const { rerender } = renderHook(({ h }) => useWS(h), {
      initialProps: { h: h1 as any },
    })
    ;(wsClient as any)._cb({ type: 'a' })
    expect(h1).toHaveBeenCalled()
    rerender({ h: h2 as any })
    ;(wsClient as any)._cb({ type: 'b' })
    expect(h2).toHaveBeenCalledWith({ type: 'b' })
  })
})

describe('useToggleTheme', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark')
    localStorage.clear()
  })

  it('toggles dark class on <html>', () => {
    const { result } = renderHook(() => useToggleTheme())
    expect(result.current.dark).toBe(false)
    act(() => result.current.toggle())
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
    act(() => result.current.toggle())
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
  })
})
