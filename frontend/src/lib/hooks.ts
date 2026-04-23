import { useEffect, useRef, useState, useCallback } from 'react'
import { wsClient } from './ws'

export function useWS(handler: (msg: any) => void) {
  const ref = useRef(handler)
  ref.current = handler
  useEffect(() => {
    const off = wsClient.on((m) => ref.current(m))
    return () => { off() }
  }, [])
}

export function useToggleTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const toggle = useCallback(() => {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
  }, [dark])
  return { dark, toggle }
}
