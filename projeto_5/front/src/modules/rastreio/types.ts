// Contratos do MOD-003 (DEC-011: snake_case).

export interface Acao {
  id: number
  descricao: string
  id_alerta: number | null
  autor: { id: number; nome: string }
  registrada_em: string
}

export interface CriarAcaoRequest {
  descricao: string
  id_alerta?: number
}

export interface AlertaResumo {
  id: number
  variavel: string
  territorio: string
  nivel: string
  limiar: number
  valor_lido: number
  lida_em: string
  status: string
}

export type ItemLinhaDoTempo =
  | { tipo: 'ALERTA'; em: string; alerta: AlertaResumo }
  | { tipo: 'ACAO'; em: string; acao: Acao }

export interface LinhaDoTempo {
  inicio: string
  fim: string
  itens: ItemLinhaDoTempo[]
}
