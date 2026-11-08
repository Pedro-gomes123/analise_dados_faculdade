import axios from 'axios'
import { clearToken, getToken } from '@/modules/auth/session'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
})

// DEC-013: o token vai no header Authorization: Bearer.
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Token expirado, inválido ou usuário inativado: volta ao login. O 401 do
// próprio login é tratado na tela.
http.interceptors.response.use(undefined, (error: unknown) => {
  if (
    axios.isAxiosError(error) &&
    error.response?.status === 401 &&
    error.config?.url !== '/auth/login'
  ) {
    clearToken()
    if (window.location.pathname !== '/login') window.location.assign('/login')
  }
  return Promise.reject(error)
})

// Corpo de erro da API (DEC-010). No 422, o detalhe por campo vem em `errors`.
export interface ApiError {
  status_code: number
  error: string
  message: string
  business_rule_code?: string
  errors?: { property: string; constraints: Record<string, string> }[]
}

export function apiErrorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

// Primeira mensagem de campo (422) ou a mensagem geral do erro.
export function apiErrorMessage(error: unknown): string | undefined {
  if (!axios.isAxiosError<ApiError>(error)) return undefined
  const body = error.response?.data
  const campo = body?.errors?.[0]?.constraints
  return (campo && Object.values(campo)[0]) ?? body?.message
}

// Texto para o usuário em qualquer falha de chamada à API.
export function describeApiError(error: unknown): string {
  const status = apiErrorStatus(error)
  if (status === undefined) return 'Não foi possível conectar ao servidor'
  if (status >= 500) return 'Erro inesperado. Tente de novo.'
  return apiErrorMessage(error) ?? 'Erro inesperado. Tente de novo.'
}
