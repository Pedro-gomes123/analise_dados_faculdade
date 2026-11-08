import { NotFoundException } from '@nestjs/common';
import type { Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import type { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { AcaoService } from '@/modules/rastreio-operacional/services/acao.service';

const AUTOR = Object.assign(new Usuario(), { id: 2, nome: 'Camila Rocha' });

function setup({ alertaExiste = true } = {}) {
  const acoes = {
    create: jest.fn((dados: Partial<Acao>) => Object.assign(new Acao(), dados)),
    save: jest.fn((acao: Acao) =>
      Promise.resolve(Object.assign(acao, { id: 7 })),
    ),
    findOne: jest.fn(() =>
      Promise.resolve(
        Object.assign(new Acao(), { id: 7, usuario: AUTOR, idUsuario: 2 }),
      ),
    ),
  };
  const alertas = { exists: jest.fn().mockResolvedValue(alertaExiste) };
  const service = new AcaoService(
    acoes as unknown as Repository<Acao>,
    alertas as unknown as Repository<Alerta>,
  );
  return { service, acoes, alertas };
}

describe('AcaoService.criar (RN-004)', () => {
  it('saves the authenticated user as author and lets the server set the time', async () => {
    const { service, acoes } = setup();

    await service.criar({ descricao: 'Equipe enviada' }, AUTOR);

    const salva = acoes.save.mock.calls[0][0];
    expect(salva).toMatchObject({
      descricao: 'Equipe enviada',
      idAlerta: null,
      idUsuario: 2,
    });
    expect(salva.dthrCriacao).toBeUndefined();
  });

  it('links the action to an existing alert (RN-004 #4)', async () => {
    const { service, acoes, alertas } = setup();

    await service.criar({ descricao: 'Equipe enviada', idAlerta: 10 }, AUTOR);

    expect(alertas.exists).toHaveBeenCalledWith({ where: { id: 10 } });
    expect(acoes.save.mock.calls[0][0]).toMatchObject({ idAlerta: 10 });
  });

  it('answers 404 for an alert that does not exist (FLX-003)', async () => {
    const { service, acoes } = setup({ alertaExiste: false });

    await expect(
      service.criar({ descricao: 'Equipe enviada', idAlerta: 99 }, AUTOR),
    ).rejects.toThrow(NotFoundException);
    expect(acoes.save).not.toHaveBeenCalled();
  });

  it('returns the saved action with its author', async () => {
    const { service, acoes } = setup();

    const acao = await service.criar({ descricao: 'Equipe enviada' }, AUTOR);

    expect(acoes.findOne).toHaveBeenCalledWith({
      where: { id: 7 },
      relations: { usuario: true },
    });
    expect(acao.usuario).toBe(AUTOR);
  });
});
