// GET /indicadores/tempo-acionamento (RN-006, PR-021). Tempos em segundos.
export interface TempoAcionamentoAlerta {
  id: number
  variavel: string
  territorio: string
  nivel: string
  disparado_em: string
  primeira_acao_em: string | null
  tempo_segundos: number | null
}

export interface TempoAcionamento {
  inicio: string
  fim: string
  media_segundos: number | null
  alertas_com_acao: number
  alertas_sem_acao: number
  alertas: TempoAcionamentoAlerta[]
}
