import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchAntarcticaData } from './api'

describe('fetchAntarcticaData', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('builds the URL with required path params and no query string', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchAntarcticaData({
      fechaIni: '2026-01-15T00:00:00',
      fechaFin: '2026-01-15T01:00:00',
      estacion: '89070',
    })

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/antartida/datos/fechaini/2026-01-15T00:00:00/fechafin/2026-01-15T01:00:00/estacion/89070',
    )
  })

  it('appends fields and aggregation as query params when provided', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchAntarcticaData({
      fechaIni: '2026-01-15T00:00:00',
      fechaFin: '2026-01-15T01:00:00',
      estacion: '89070',
      fields: ['temperature', 'speed'],
      aggregation: 'daily',
    })

    const calledUrl = fetchMock.mock.calls[0][0] as string
    expect(calledUrl).toContain('fields=temperature%2Cspeed')
    expect(calledUrl).toContain('aggregation=daily')
  })

  it('throws with the API error message when the response is not ok', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Invalid station' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      fetchAntarcticaData({
        fechaIni: '2026-01-15T00:00:00',
        fechaFin: '2026-01-15T01:00:00',
        estacion: '99999' as '89070',
      }),
    ).rejects.toThrow('Invalid station')
  })
})