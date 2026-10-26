import { montarLinhaDoTempo } from '@/modules/rastreio-operacional/domain/linha-do-tempo';

const t = (hhmm: string) => new Date(`2026-11-02T${hhmm}:00.000Z`);

describe('montarLinhaDoTempo (RN-005)', () => {
  it('merges alerts and actions in chronological order', () => {
    const itens = montarLinhaDoTempo(
      [
        { em: t('10:00'), alerta: 'A1' },
        { em: t('12:00'), alerta: 'A2' },
      ],
      [
        { em: t('13:00'), acao: 'C2' },
        { em: t('10:20'), acao: 'C1' },
      ],
    );

    expect(itens.map((i) => (i.tipo === 'ALERTA' ? i.alerta : i.acao))).toEqual(
      ['A1', 'C1', 'A2', 'C2'],
    );
  });

  it('puts the alert before an action at the same instant', () => {
    const itens = montarLinhaDoTempo(
      [{ em: t('10:00'), alerta: 'A1' }],
      [{ em: t('10:00'), acao: 'C1' }],
    );

    expect(itens.map((i) => i.tipo)).toEqual(['ALERTA', 'ACAO']);
  });

  it('is empty for an empty period', () => {
    expect(montarLinhaDoTempo([], [])).toEqual([]);
  });
});
