import { diferencaParametro } from '@/modules/alertas/domain/diferenca-parametro';
import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';

const ATUAL = { limiar: 50, nivel: 'ALTO', ativo: true };

describe('diferencaParametro (RN-001)', () => {
  it('keeps only the changed fields, before and after (#2)', () => {
    expect(diferencaParametro(ATUAL, { limiar: 60, nivel: 'ALTO' })).toEqual({
      operacao: OperacaoHistorico.Alteracao,
      anterior: { limiar: 50 },
      novo: { limiar: 60 },
    });
  });

  it('records a deactivation as its own operation (#3)', () => {
    expect(diferencaParametro(ATUAL, { ativo: false, nivel: 'MEDIO' })).toEqual(
      {
        operacao: OperacaoHistorico.Inativacao,
        anterior: { nivel: 'ALTO', ativo: true },
        novo: { nivel: 'MEDIO', ativo: false },
      },
    );
  });

  it('records a reactivation as a change', () => {
    expect(
      diferencaParametro({ ...ATUAL, ativo: false }, { ativo: true }),
    ).toMatchObject({ operacao: OperacaoHistorico.Alteracao });
  });

  it('is null when nothing changes', () => {
    expect(diferencaParametro(ATUAL, {})).toBeNull();
    expect(diferencaParametro(ATUAL, { limiar: 50, ativo: true })).toBeNull();
  });
});
