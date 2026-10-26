import { http } from '@/lib/http'

export interface HealthResponse {
  status: 'ok' | 'error' | 'shutting_down'
  info?: Record<string, { status: string }>
  error?: Record<string, { status: string }>
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
  return data
}
