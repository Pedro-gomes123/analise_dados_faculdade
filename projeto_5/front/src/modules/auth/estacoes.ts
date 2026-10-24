import { PAPEIS } from '@/modules/auth/papeis'
import type { Papel } from '@/modules/auth/types'

// Estação de cada papel (permissoes.md, REQ-008 a REQ-011). ADM não tem
// estação: abre a administração de usuários (PER-003).
export const ROTA_POR_PAPEL = {
  TEC: '/estacoes/est-01',
  GES: '/estacoes/est-02',
  GIN: '/estacoes/est-03',
  COM: '/estacoes/est-04',
  ADM: '/usuarios',
} as const satisfies Record<Papel, string>

export type RotaInicial = (typeof ROTA_POR_PAPEL)[Papel]

const CODIGO_POR_PAPEL: Record<Papel, string> = {
  TEC: 'EST-01',
  GES: 'EST-02',
  GIN: 'EST-03',
  COM: 'EST-04',
  ADM: 'ADM',
}

// O que cada estação reúne (REQ-008 a REQ-011).
const DESCRICAO_POR_PAPEL: Record<Papel, string> = {
  TEC: 'Painel operacional: dados meteorológicos e hidrológicos, indicadores e boletim técnico',
  GES: 'Mapa de risco, alertas automáticos por parâmetro e linha do tempo do evento',
  GIN: 'Pessoas em risco, cobertura de resposta e tempo médio de acionamento',
  COM: 'Montagem e pré-visualização do boletim para publicação',
  ADM: 'Contas, papéis e acesso ao sistema',
}

export interface Estacao {
  papel: Papel
  codigo: string
  titulo: string
  descricao: string
  rota: RotaInicial
}

// Itens do menu, na ordem EST-01 a EST-04 e depois ADM.
export const ESTACOES: Estacao[] = PAPEIS.map(({ valor, rotulo }) => ({
  papel: valor,
  codigo: CODIGO_POR_PAPEL[valor],
  titulo: valor === 'ADM' ? 'Usuários' : rotulo,
  descricao: DESCRICAO_POR_PAPEL[valor],
  rota: ROTA_POR_PAPEL[valor],
}))

// REQ-013: cada perfil só vê as estações dos seus papéis (união, AM-004 c).
export function estacoesDoUsuario(papeis: Papel[]): Estacao[] {
  return ESTACOES.filter((estacao) => papeis.includes(estacao.papel))
}

// FLX-001 "abre a estação do primeiro papel". O back ordena os papéis em ordem
// alfabética, então a prioridade é fixa: EST-01 a EST-04, depois ADM.
export function rotaInicial(papeis: Papel[]): RotaInicial | null {
  return estacoesDoUsuario(papeis)[0]?.rota ?? null
}

export function temPapel(papeis: Papel[], permitidos: Papel[]): boolean {
  return papeis.some((p) => permitidos.includes(p))
}
