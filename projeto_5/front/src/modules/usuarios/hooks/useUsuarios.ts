import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authKeys } from '@/modules/auth/hooks/useAuth'
import {
  alterarUsuario,
  criarUsuario,
  listarUsuarios,
} from '@/modules/usuarios/service/usuarios.service'
import type { AlterarUsuarioRequest, ListarUsuariosParams } from '@/modules/usuarios/types'

export const usuariosKeys = {
  all: ['usuarios'] as const,
  list: (params: ListarUsuariosParams) => ['usuarios', 'list', params] as const,
}

export function useUsuariosQuery(params: ListarUsuariosParams) {
  return useQuery({
    queryKey: usuariosKeys.list(params),
    queryFn: () => listarUsuarios(params),
    placeholderData: keepPreviousData,
  })
}

export function useCriarUsuario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: criarUsuario,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usuariosKeys.all }),
  })
}

export function useAlterarUsuario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: AlterarUsuarioRequest }) =>
      alterarUsuario(id, dados),
    onSuccess: async () => {
      // O ADM pode ter alterado a própria conta (nome ou papéis no cabeçalho).
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: usuariosKeys.all }),
        queryClient.invalidateQueries({ queryKey: authKeys.me }),
      ])
    },
  })
}
