import {
  calcularTempoAcionamento,
  tempoAcionamentoMs,
  type AlertaComAcoes,
} from '@/modules/rastreio-operacional/domain/calcular-tempo-acionamento';

const MINUTO = 60_000;
const DISPARO = new Date('2026-11-10T12:00:00.000Z');

function alerta(...minutosDasAcoes: number[]): AlertaComAcoes {
  return {
    dthrDisparo: DISPARO,
    acoes: minutosDasAcoes.map((m) => ({
      dthrCriacao: new Date(DISPARO.getTime() + m * MINUTO),
    })),
  };
}

describe('tempoAcionamentoMs (RN-006 #1)', () => {
  it('measures from trigger to the only action', () => {
    expect(tempoAcionamentoMs(alerta(15))).toBe(15 * MINUTO);
  });

  it('uses the first action, whatever the input order', () => {
    expect(tempoAcionamentoMs(alerta(40, 10, 25))).toBe(10 * MINUTO);
  });

  it('is null for an alert without actions', () => {
    expect(tempoAcionamentoMs(alerta())).toBeNull();
  });
});

describe('calcularTempoAcionamento (RN-006 #2, #3)', () => {
  it('averages the response time of the alerts', () => {
    expect(calcularTempoAcionamento([alerta(10), alerta(30, 50)])).toEqual({
      mediaMs: 20 * MINUTO,
      alertasComAcao: 2,
      alertasSemAcao: 0,
    });
  });

  it('counts alerts without action apart, outside the average (PR-021)', () => {
    expect(
      calcularTempoAcionamento([alerta(10), alerta(), alerta(20), alerta()]),
    ).toEqual({ mediaMs: 15 * MINUTO, alertasComAcao: 2, alertasSemAcao: 2 });
  });

  it('has no average when no alert has an action', () => {
    expect(calcularTempoAcionamento([alerta(), alerta()])).toEqual({
      mediaMs: null,
      alertasComAcao: 0,
      alertasSemAcao: 2,
    });
  });

  it('has no average for an empty period', () => {
    expect(calcularTempoAcionamento([])).toEqual({
      mediaMs: null,
      alertasComAcao: 0,
      alertasSemAcao: 0,
    });
  });
});
