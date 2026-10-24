import { NotFoundException } from '@nestjs/common';
import type { DataSource, EntityManager, Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';
import { ParametroAlertaService } from '@/modules/alertas/services/parametro-alerta.service';

const GESTOR = Object.assign(new Usuario(), { id: 2, nome: 'Camila Rocha' });

function parametro(overrides: Partial<ParametroAlerta> = {}): ParametroAlerta {
  return Object.assign(new ParametroAlerta(), {
    id: 3,
    variavel: 'chuva_1h',
    territorio: 'RPA-1',
    limiar: 50,
    nivel: 'ALTO',
    ativo: true,
    ...overrides,
  });
}

function setup(existente: ParametroAlerta | null = parametro()) {
  const manager = {
    create: jest.fn((_: unknown, dados: Partial<ParametroAlerta>) =>
      Object.assign(new ParametroAlerta(), dados),
    ),
    save: jest.fn((p: ParametroAlerta) =>
      Promise.resolve(Object.assign(p, { id: p.id ?? 3 })),
    ),
    insert: jest.fn().mockResolvedValue(undefined),
    findOne: jest.fn().mockResolvedValue(existente),
  };
  const dataSource = {
    transaction: jest.fn((work: (m: EntityManager) => Promise<unknown>) =>
      work(manager as unknown as EntityManager),
    ),
  };
  const parametros = { exists: jest.fn().mockResolvedValue(!!existente) };
  const service = new ParametroAlertaService(
    parametros as unknown as Repository<ParametroAlerta>,
    {} as Repository<ParametroAlertaHistorico>,
    dataSource as unknown as DataSource,
  );
  return { service, manager, dataSource };
}

const novo = {
  variavel: 'chuva_1h',
  territorio: 'RPA-1',
  limiar: 50,
  nivel: 'ALTO',
};

describe('ParametroAlertaService (RN-001)', () => {
  it('creates the parameter active with a CRIACAO history line (#1)', async () => {
    const { service, manager, dataSource } = setup();

    await service.criar(novo, GESTOR);

    expect(dataSource.transaction).toHaveBeenCalledTimes(1);
    expect(manager.save.mock.calls[0][0]).toMatchObject({
      ...novo,
      ativo: true,
    });
    expect(manager.insert).toHaveBeenCalledWith(ParametroAlertaHistorico, {
      idParametroAlerta: 3,
      idUsuario: 2,
      operacao: OperacaoHistorico.Criacao,
      valorAnterior: null,
      valorNovo: { ...novo, ativo: true },
    });
  });

  it('records only the changed fields with before and after (#2)', async () => {
    const { service, manager } = setup();

    const salvo = await service.alterar(
      3,
      { limiar: 60, nivel: 'ALTO' },
      GESTOR,
    );

    expect(salvo.limiar).toBe(60);
    expect(manager.insert).toHaveBeenCalledWith(ParametroAlertaHistorico, {
      idParametroAlerta: 3,
      idUsuario: 2,
      operacao: OperacaoHistorico.Alteracao,
      valorAnterior: { limiar: 50 },
      valorNovo: { limiar: 60 },
    });
  });

  it('records the deactivation (#3)', async () => {
    const { service, manager } = setup();

    const salvo = await service.alterar(3, { ativo: false }, GESTOR);

    expect(salvo.ativo).toBe(false);
    expect(manager.insert).toHaveBeenCalledWith(
      ParametroAlertaHistorico,
      expect.objectContaining({ operacao: OperacaoHistorico.Inativacao }),
    );
  });

  it('reads the previous value with a row lock inside the transaction (concurrency)', async () => {
    const { service, manager } = setup();

    await service.alterar(3, { limiar: 60 }, GESTOR);

    expect(manager.findOne).toHaveBeenCalledWith(ParametroAlerta, {
      where: { id: 3 },
      lock: { mode: 'pessimistic_write' },
    });
  });

  it('writes nothing when nothing changes', async () => {
    const { service, manager } = setup();

    await service.alterar(3, { limiar: 50 }, GESTOR);

    expect(manager.save).not.toHaveBeenCalled();
    expect(manager.insert).not.toHaveBeenCalled();
  });

  it('answers 404 for a missing parameter', async () => {
    const { service } = setup(null);

    await expect(service.alterar(9, { limiar: 1 }, GESTOR)).rejects.toThrow(
      NotFoundException,
    );
    await expect(service.historico(9, { path: '' })).rejects.toThrow(
      NotFoundException,
    );
  });

  it('fails the whole change if the history cannot be written (#4)', async () => {
    const { service, manager } = setup();
    manager.insert.mockRejectedValue(new Error('falha ao gravar histórico'));

    await expect(service.alterar(3, { limiar: 60 }, GESTOR)).rejects.toThrow(
      'falha ao gravar histórico',
    );
  });
});
