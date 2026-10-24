import { http } from '@/lib/http'
import type { LoginRequest, LoginResponse, Usuario } from '@/modules/auth/types'

export async function login(dados: LoginRequest): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', dados)
  return data
}

export async function getMe(): Promise<Usuario> {
  const { data } = await http.get<Usuario>('/auth/me')
  return data
}
