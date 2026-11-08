import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  alterarParametro,
  criarParametro,
  listarAlertas,
  listarHistorico,
  listarParametros,
  type ListarAlertasParams,
} from '@/modules/alertas/service/alertas.service'
import type { AlterarParametroRequest } from '@/modules/alertas/types'

export const alertasKeys = {
  lista: (params: ListarAlertasParams) => ['alertas', params] as const,
}

export const parametrosKeys = {
  all: ['parametros-alerta'] as const,
  lista: (page: number) => ['parametros-alerta', 'lista', page] as const,
  historico: (id: number, page: number) => ['parametros-alerta', id, 'historico', page] as const,
}

export function useAlertasQuery(params: ListarAlertasParams) {
  return useQuery({
    queryKey: alertasKeys.lista(params),
    queryFn: () => listarAlertas(params),
    placeholderData: keepPreviousData,
  })
}

export function useParametrosQuery(page: number) {
  return useQuery({
    queryKey: parametrosKeys.lista(page),
    queryFn: () => listarParametros(page),
    placeholderData: keepPreviousData,
  })
}

export function useHistoricoQuery(id: number, page: number) {
  return useQuery({
    queryKey: parametrosKeys.historico(id, page),
    queryFn: () => listarHistorico(id, page),
    placeholderData: keepPreviousData,
  })
}

export function useCriarParametro() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: criarParametro,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: parametrosKeys.all }),
  })
}

export function useAlterarParametro() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, dados }: { id: number; dados: AlterarParametroRequest }) =>
      alterarParametro(id, dados),
    // Lista e histórico do parâmetro mudam juntos (RN-001).
    onSuccess: () => queryClient.invalidateQueries({ queryKey: parametrosKeys.all }),
  })
}
