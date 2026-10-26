import { http } from '@/lib/http'
import type { Intervalo } from '@/lib/periodo'
import type { TempoAcionamento } from '@/modules/indicadores/types'

export async function consultarTempoAcionamento(intervalo: Intervalo): Promise<TempoAcionamento> {
  const { data } = await http.get<TempoAcionamento>('/indicadores/tempo-acionamento', {
    params: intervalo,
  })
  return data
}
