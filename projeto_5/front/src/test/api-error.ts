import { AxiosError, AxiosHeaders } from 'axios'
import type { ApiError } from '@/lib/http'

// Erro do axios com o corpo da API (DEC-010), para os testes.
export function apiError(status: number, body: Partial<ApiError> = {}) {
  return new AxiosError('falha', String(status), undefined, undefined, {
    status,
    statusText: '',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: { status_code: status, error: '', message: 'erro', ...body },
  })
}
