import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from './api'

const mkResp = (status: number, body: any, ct = 'application/json'): any => ({
  ok: status >= 200 && status < 300,
  status,
  headers: { get: (_: string) => ct },
  json: async () => body,
  text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
})

describe('api', () => {
  beforeEach(() => { vi.restoreAllMocks() })

  it('GET parses JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mkResp(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    const r = await api.get<{ ok: boolean }>('/api/x')
    expect(r.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith('/api/x', expect.any(Object))
  })

  it('throws on non-2xx with status and body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mkResp(404, 'not found', 'text/plain')))
    await expect(api.get('/api/missing')).rejects.toThrow(/404/)
  })

  it('POST stringifies body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mkResp(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await api.post('/api/x', { a: 1 })
    expect(fetchMock.mock.calls[0][1].body).toBe('{"a":1}')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
  })

  it('DELETE has no body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mkResp(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await api.del('/api/x/1')
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE')
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined()
  })

  it('upload posts FormData with files', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mkResp(200, [{ id: 1 }]))
    vi.stubGlobal('fetch', fetchMock)
    const f = new File(['x'], 'a.jpg', { type: 'image/jpeg' })
    const out = await api.upload<any>('/api/images/upload', [f])
    expect(out).toEqual([{ id: 1 }])
    expect(fetchMock.mock.calls[0][1].body).toBeInstanceOf(FormData)
  })

  it('returns text when content-type is not json', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mkResp(200, 'plain', 'text/plain')))
    const r = await api.get<string>('/api/text')
    expect(r).toBe('plain')
  })
})
