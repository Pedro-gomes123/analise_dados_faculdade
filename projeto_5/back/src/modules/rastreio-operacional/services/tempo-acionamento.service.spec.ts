import type { Repository } from 'typeorm';
import type { Alerta } from '@/modules/alertas/entities/alerta.entity';
import {
  montarTempoAcionamento,
  TempoAcionamentoService,
  type AlertaComPrimeiraAcao,
} from '@/modules/rastreio-operacional/services/tempo-acionamento.service';

const PERIODO = {
  inicio: new Date('2026-11-01T00:00:00.000Z'),
  fim: new Date('2026-11-07T23:59:59.999Z'),
};

function linha(
  id: number,
  disparo: string,
  primeiraAcao: string | null,
): AlertaComPrimeiraAcao {
  return {
    id,
    variavel: 'chuva_1h',
    territorio: 'RPA-1',
    nivel: 'ALTO',
    dthr_disparo: new Date(disparo),
    primeira_acao_em: primeiraAcao ? new Date(primeiraAcao) : null,
  };
}

describe('montarTempoAcionamento (RN-006, PR-021)', () => {
  it('gives each alert its time in seconds and the average of those with action', () => {
    const resposta = montarTempoAcionamento(PERIODO, [
      linha(1, '2026-11-02T10:00:00Z', '2026-11-02T10:10:00Z'),
      linha(2, '2026-11-03T10:00:00Z', null),
      linha(3, '2026-11-04T10:00:00Z', '2026-11-04T10:30:00Z'),
    ]);

    expect(resposta).toMatchObject({
      inicio: PERIODO.inicio,
      fim: PERIODO.fim,
      media_segundos: 1200,
      alertas_com_acao: 2,
      alertas_sem_acao: 1,
    });
    expect(resposta.alertas.map((a) => [a.id, a.tempo_segundos])).toEqual([
      [1, 600],
      [2, null],
      [3, 1800],
    ]);
    expect(resposta.alertas[1]).toMatchObject({
      primeira_acao_em: null,
      disparado_em: new Date('2026-11-03T10:00:00Z'),
    });
  });

  it('rounds to whole seconds', () => {
    const resposta = montarTempoAcionamento(PERIODO, [
      linha(1, '2026-11-02T10:00:00.000Z', '2026-11-02T10:00:01.600Z'),
    ]);

    expect(resposta.media_segundos).toBe(2);
    expect(resposta.alertas[0].tempo_segundos).toBe(2);
  });

  it('has no average for a period without alerts', () => {
    expect(montarTempoAcionamento(PERIODO, [])).toMatchObject({
      media_segundos: null,
      alertas_com_acao: 0,
      alertas_sem_acao: 0,
      alertas: [],
    });
  });
});

describe('TempoAcionamentoService', () => {
  it('filters alerts by trigger time in the period and keeps the first action', async () => {
    const qb = {
      leftJoin: jest.fn().mockReturnThis(),
      select: jest.fn().mockReturnThis(),
      addSelect: jest.fn().mockReturnThis(),
      where: jest.fn().mockReturnThis(),
      groupBy: jest.fn().mockReturnThis(),
      addGroupBy: jest.fn().mockReturnThis(),
      orderBy: jest.fn().mockReturnThis(),
      getRawMany: jest
        .fn()
        .mockResolvedValue([
          linha(1, '2026-11-02T10:00:00Z', '2026-11-02T10:05:00Z'),
        ]),
    };
    const repo = { createQueryBuilder: jest.fn(() => qb) };
    const service = new TempoAcionamentoService(
      repo as unknown as Repository<Alerta>,
    );

    const resposta = await service.calcular(PERIODO);

    expect(qb.where).toHaveBeenCalledWith(
      'alerta.dthr_disparo BETWEEN :inicio AND :fim',
      PERIODO,
    );
    expect(qb.addSelect).toHaveBeenCalledWith(
      'MIN(acao.dthr_criacao)',
      'primeira_acao_em',
    );
    expect(qb.orderBy).toHaveBeenCalledWith('alerta.dthr_disparo', 'ASC');
    expect(resposta.media_segundos).toBe(300);
  });
});
