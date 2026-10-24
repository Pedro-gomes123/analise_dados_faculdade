import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { intervaloDoPeriodo, type Periodo } from '@/lib/periodo'
import { consultarTempoAcionamento } from '@/modules/indicadores/service/indicadores.service'

// Prefixo 'indicadores': registrar uma ação invalida estes dados (useCriarAcao).
export const indicadoresKeys = {
  tempoAcionamento: (periodo: Periodo) => ['indicadores', 'tempo-acionamento', periodo] as const,
}

export function useTempoAcionamentoQuery(periodo: Periodo) {
  return useQuery({
    queryKey: indicadoresKeys.tempoAcionamento(periodo),
    queryFn: () => consultarTempoAcionamento(intervaloDoPeriodo(periodo)),
    placeholderData: keepPreviousData,
  })
}
