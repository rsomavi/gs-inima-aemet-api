import type { AggregationLevel, FieldName, Measurement, StationCode } from './types'

const API_BASE_URL = 'http://localhost:8000/api'

export interface QueryParams {
  fechaIni: string
  fechaFin: string
  estacion: StationCode
  fields?: FieldName[]
  aggregation?: AggregationLevel
  location?: string
}

export async function fetchAntarcticaData(params: QueryParams): Promise<Measurement[]> {
  const url = buildUrl(params)

  const response = await fetch(url)

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorBody.error ?? `Request failed with status ${response.status}`)
  }

  return response.json()
}

function buildUrl(params: QueryParams): string {
  const path = `${API_BASE_URL}/antartida/datos/fechaini/${params.fechaIni}/fechafin/${params.fechaFin}/estacion/${params.estacion}`

  const query = new URLSearchParams()
  if (params.fields && params.fields.length > 0) {
    query.set('fields', params.fields.join(','))
  }
  if (params.aggregation) {
    query.set('aggregation', params.aggregation)
  }
  if (params.location) {
    query.set('location', params.location)
  }

  const queryString = query.toString()
  return queryString ? `${path}?${queryString}` : path
}