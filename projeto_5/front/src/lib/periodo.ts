// Filtros de período do MVP (PR-018): 24 h, 7 e 30 dias até agora.
export type Periodo = '24h' | '7d' | '30d'

export const PERIODOS: { valor: Periodo; rotulo: string; horas: number }[] = [
  { valor: '24h', rotulo: 'Últimas 24 h', horas: 24 },
  { valor: '7d', rotulo: '7 dias', horas: 24 * 7 },
  { valor: '30d', rotulo: '30 dias', horas: 24 * 30 },
]

export interface Intervalo {
  inicio: string
  fim: string
}

// Calculado na hora da consulta, para "agora" não ficar parado no cache.
export function intervaloDoPeriodo(periodo: Periodo, agora = new Date()): Intervalo {
  const { horas } = PERIODOS.find((p) => p.valor === periodo)!
  return {
    inicio: new Date(agora.getTime() - horas * 3_600_000).toISOString(),
    fim: agora.toISOString(),
  }
}
