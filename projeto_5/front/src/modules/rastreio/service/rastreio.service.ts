import { http } from '@/lib/http'
import type { Intervalo } from '@/lib/periodo'
import type { Acao, CriarAcaoRequest, LinhaDoTempo } from '@/modules/rastreio/types'

export async function criarAcao(dados: CriarAcaoRequest): Promise<Acao> {
  const { data } = await http.post<Acao>('/acoes', dados)
  return data
}

export async function consultarLinhaDoTempo(intervalo: Intervalo): Promise<LinhaDoTempo> {
  const { data } = await http.get<LinhaDoTempo>('/linha-do-tempo', { params: intervalo })
  return data
}
