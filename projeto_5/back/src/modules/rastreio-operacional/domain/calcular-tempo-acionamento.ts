// RN-006: response time = first linked action - alert trigger time.

export interface AlertaComAcoes {
  dthrDisparo: Date;
  acoes: { dthrCriacao: Date }[];
}

export interface TempoAcionamento {
  /** Average in milliseconds over alerts with at least one action; null if none. */
  mediaMs: number | null;
  alertasComAcao: number;
  /** RN-006 #3 (DUV-032): reported apart, not averaged (PR-021). */
  alertasSemAcao: number;
}

// RN-006 #1. Null when the alert has no linked action.
export function tempoAcionamentoMs(alerta: AlertaComAcoes): number | null {
  if (alerta.acoes.length === 0) return null;
  const primeira = Math.min(
    ...alerta.acoes.map((a) => a.dthrCriacao.getTime()),
  );
  return primeira - alerta.dthrDisparo.getTime();
}

// RN-006 #2: average over the alerts of the period.
export function calcularTempoAcionamento(
  alertas: AlertaComAcoes[],
): TempoAcionamento {
  const tempos = alertas
    .map(tempoAcionamentoMs)
    .filter((tempo): tempo is number => tempo !== null);

  return {
    mediaMs:
      tempos.length === 0
        ? null
        : tempos.reduce((soma, tempo) => soma + tempo, 0) / tempos.length,
    alertasComAcao: tempos.length,
    alertasSemAcao: alertas.length - tempos.length,
  };
}
