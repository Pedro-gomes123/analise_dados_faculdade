import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { intervaloDoPeriodo, type Periodo } from '@/lib/periodo'
import { consultarLinhaDoTempo, criarAcao } from '@/modules/rastreio/service/rastreio.service'

export const rastreioKeys = {
  linhaDoTempo: (periodo: Periodo) => ['linha-do-tempo', periodo] as const,
}

export function useLinhaDoTempoQuery(periodo: Periodo) {
  return useQuery({
    queryKey: rastreioKeys.linhaDoTempo(periodo),
    queryFn: () => consultarLinhaDoTempo(intervaloDoPeriodo(periodo)),
    placeholderData: keepPreviousData,
  })
}

export function useCriarAcao() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: criarAcao,
    // FLX-003: a linha do tempo e o tempo de acionamento mudam com a ação.
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['linha-do-tempo'] }),
        queryClient.invalidateQueries({ queryKey: ['indicadores'] }),
      ]),
  })
}
