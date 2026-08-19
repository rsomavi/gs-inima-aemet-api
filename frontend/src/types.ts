// Shape of a single measurement returned by the backend API.
// Temperature/Pressure/Speed are optional because the `fields`
// query param can request any subset of them.
export interface Measurement {
  Station: string
  Datetime: string
  'Temperature (ºC)'?: number | null
  'Pressure (hpa)'?: number | null
  'Speed (m/s)'?: number | null
}

export const STATIONS = {
  '89070': 'Meteo Station Gabriel de Castilla',
  '89064': 'Meteo Station Juan Carlos I',
} as const

export type StationCode = keyof typeof STATIONS

export type AggregationLevel = 'none' | 'hourly' | 'daily' | 'monthly'

export type FieldName = 'temperature' | 'pressure' | 'speed'