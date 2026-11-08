export class TempoAcionamentoAlertaDto {
  id!: number;
  variavel!: string;
  territorio!: string;
  nivel!: string;
  disparado_em!: Date;
  /** Nulo quando o alerta não tem ação ligada (PR-021) */
  primeira_acao_em!: Date | null;
  /** Nulo quando o alerta não tem ação ligada (PR-021) */
  tempo_segundos!: number | null;
}

// RN-006 / REQ-018 (EST-03). Times in whole seconds.
export class TempoAcionamentoResponseDto {
  inicio!: Date;
  fim!: Date;
  /** Média dos alertas com ação; nula se nenhum teve ação */
  media_segundos!: number | null;
  alertas_com_acao!: number;
  /** Fora da média, contados à parte (PR-021) */
  alertas_sem_acao!: number;
  alertas!: TempoAcionamentoAlertaDto[];
}
