import type { QueryClient } from '@tanstack/react-query'
import { redirect } from '@tanstack/react-router'
import { rotaInicial, temPapel } from '@/modules/auth/estacoes'
import { meQueryOptions } from '@/modules/auth/hooks/useAuth'
import { clearToken, getToken } from '@/modules/auth/session'
import type { Papel, Usuario } from '@/modules/auth/types'

// Usuário logado ou null (sem token, token inválido ou usuário inativado).
export async function carregarUsuario(queryClient: QueryClient): Promise<Usuario | null> {
  if (!getToken()) return null
  try {
    return await queryClient.ensureQueryData(meQueryOptions)
  } catch {
    clearToken()
    return null
  }
}

// O bloqueio no front é só experiência de uso; quem recusa é o back (permissoes.md).
export function exigirPapel(usuario: Usuario, permitidos: Papel[]) {
  if (!temPapel(usuario.papeis, permitidos)) {
    throw redirect({ to: rotaInicial(usuario.papeis) ?? '/login' })
  }
}
