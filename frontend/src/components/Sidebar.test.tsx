/// <reference lib="dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { api } from '../lib/api'
import { wsClient } from '../lib/ws'

beforeEach(() => {
  vi.spyOn(wsClient, 'on').mockReturnValue(() => {})
})

describe('Sidebar', () => {
  it('renders TV names from API', async () => {
    vi.spyOn(api, 'get').mockImplementation(async (path: string) => {
      if (path === '/api/tvs') {
        return [
          { id: 1, name: 'Living', ip: '10.0.0.1', port: 8002, added_at: '' },
          { id: 2, name: 'Bedroom', ip: '10.0.0.2', port: 8002, added_at: '' },
        ] as any
      }
      if (path.endsWith('/status')) {
        return { id: 1, online: true, artmode: true, current: null, paired: true } as any
      }
      return [] as any
    })

    render(<MemoryRouter><Sidebar /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Living')).toBeInTheDocument()
      expect(screen.getByText('Bedroom')).toBeInTheDocument()
    })
  })

  it('fetches statuses in parallel (Promise.all)', async () => {
    const calls: string[] = []
    let concurrent = 0
    let max = 0
    vi.spyOn(api, 'get').mockImplementation(async (path: string) => {
      calls.push(path)
      if (path === '/api/tvs') {
        return [
          { id: 1, name: 'A', ip: '10.0.0.1', port: 8002, added_at: '' },
          { id: 2, name: 'B', ip: '10.0.0.2', port: 8002, added_at: '' },
          { id: 3, name: 'C', ip: '10.0.0.3', port: 8002, added_at: '' },
        ] as any
      }
      concurrent++
      max = Math.max(max, concurrent)
      await new Promise((r) => setTimeout(r, 10))
      concurrent--
      return { id: 1, online: true } as any
    })
    render(<MemoryRouter><Sidebar /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('A')).toBeInTheDocument()
    })
    await new Promise((r) => setTimeout(r, 30))
    expect(max).toBeGreaterThan(1)  // confirms parallel
  })

  it('handles status fetch failure gracefully', async () => {
    vi.spyOn(api, 'get').mockImplementation(async (path: string) => {
      if (path === '/api/tvs') {
        return [{ id: 1, name: 'Solo', ip: '10.0.0.1', port: 8002, added_at: '' }] as any
      }
      throw new Error('boom')
    })
    render(<MemoryRouter><Sidebar /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Solo')).toBeInTheDocument())
    // Should still render TV with neutral dot, no crash
  })

  it('renders empty-state when no TVs', async () => {
    vi.spyOn(api, 'get').mockResolvedValue([] as any)
    render(<MemoryRouter><Sidebar /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('None added')).toBeInTheDocument())
  })
})
