import { http } from '@/lib/http'
import type { Paginated } from '@/lib/pagination'
import type {
  Alerta,
  AlterarParametroRequest,
  CriarParametroRequest,
  HistoricoParametro,
  ParametroAlerta,
  StatusAlerta,
} from '@/modules/alertas/types'

export const ITENS_POR_PAGINA = 20

export interface ListarAlertasParams {
  page: number
  /** Sem status: ativos e encerrados (histórico) */
  status?: StatusAlerta
}

export async function listarAlertas({ page, status }: ListarAlertasParams) {
  const { data } = await http.get<Paginated<Alerta>>('/alertas', {
    params: {
      page,
      limit: ITENS_POR_PAGINA,
      ...(status && { 'filter.status': `$eq:${status}` }),
    },
  })
  return data
}

export async function listarParametros(page: number) {
  const { data } = await http.get<Paginated<ParametroAlerta>>('/parametros-alerta', {
    params: { page, limit: ITENS_POR_PAGINA },
  })
  return data
}

export async function listarHistorico(id: number, page: number) {
  const { data } = await http.get<Paginated<HistoricoParametro>>(
    `/parametros-alerta/${id}/historico`,
    { params: { page, limit: ITENS_POR_PAGINA } },
  )
  return data
}

export async function criarParametro(dados: CriarParametroRequest) {
  const { data } = await http.post<ParametroAlerta>('/parametros-alerta', dados)
  return data
}

export async function alterarParametro(id: number, dados: AlterarParametroRequest) {
  const { data } = await http.patch<ParametroAlerta>(`/parametros-alerta/${id}`, dados)
  return data
}
