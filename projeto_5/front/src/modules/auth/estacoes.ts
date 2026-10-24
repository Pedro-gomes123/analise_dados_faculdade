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

// FLX-001 "abre a estação do primeiro papel". O back ordena os papéis em ordem
// alfabética, então a prioridade é fixa aqui: EST-01 a EST-04, depois ADM.
const PRIORIDADE: Papel[] = ['TEC', 'GES', 'GIN', 'COM', 'ADM']

export function rotaInicial(papeis: Papel[]): RotaInicial | null {
  const papel = PRIORIDADE.find((p) => papeis.includes(p))
  return papel ? ROTA_POR_PAPEL[papel] : null
}

export function temPapel(papeis: Papel[], permitidos: Papel[]): boolean {
  return papeis.some((p) => permitidos.includes(p))
}
