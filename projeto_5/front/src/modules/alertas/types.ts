// Contratos do MOD-002 (DEC-011: snake_case).

export type StatusAlerta = 'ATIVO' | 'ENCERRADO'

export interface Alerta {
  id: number
  nivel: string
  parametro: { id: number; variavel: string; limiar: number }
  territorio: string
  valor_lido: number
  fonte: string
  lida_em: string
  disparado_em: string
  /** Nulo até o contrato do gold (DEC-009, RN-007 #2) */
  fonte_atualizada_em: string | null
  status: StatusAlerta
}

export interface ParametroAlerta {
  id: number
  variavel: string
  territorio: string
  limiar: number
  nivel: string
  ativo: boolean
  atualizado_em: string
}

export interface CriarParametroRequest {
  variavel: string
  territorio: string
  limiar: number
  nivel: string
}

// Variável e território identificam o parâmetro e não mudam.
export interface AlterarParametroRequest {
  limiar?: number
  nivel?: string
  ativo?: boolean
}

export type OperacaoHistorico = 'CRIACAO' | 'ALTERACAO' | 'INATIVACAO'

export interface HistoricoParametro {
  id: number
  operacao: OperacaoHistorico
  valor_anterior: Record<string, unknown> | null
  valor_novo: Record<string, unknown>
  autor: { id: number; nome: string }
  registrado_em: string
}
