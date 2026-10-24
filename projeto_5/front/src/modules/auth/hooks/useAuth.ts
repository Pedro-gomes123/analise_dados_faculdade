import { queryOptions, useMutation, useQueryClient, useSuspenseQuery } from '@tanstack/react-query'
import { getMe, login } from '@/modules/auth/service/auth.service'
import { clearToken, setToken } from '@/modules/auth/session'

export const authKeys = {
  me: ['auth', 'me'] as const,
}

// Papéis e "ativo" vêm sempre do back (DEC-013): o token só leva o id.
export const meQueryOptions = queryOptions({
  queryKey: authKeys.me,
  queryFn: getMe,
  staleTime: 5 * 60_000,
  retry: false,
})

export function useUsuarioAtual() {
  return useSuspenseQuery(meQueryOptions).data
}

export function useLoginMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: login,
    onSuccess: ({ access_token, usuario }) => {
      setToken(access_token)
      queryClient.setQueryData(authKeys.me, usuario)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return () => {
    clearToken()
    queryClient.clear()
  }
}
