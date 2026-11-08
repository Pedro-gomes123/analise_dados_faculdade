import { Between, type Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { StatusAlerta } from '@/modules/alertas/enums/status-alerta.enum';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { LinhaDoTempoService } from '@/modules/rastreio-operacional/services/linha-do-tempo.service';

const PERIODO = {
  inicio: new Date('2026-11-02T00:00:00.000Z'),
  fim: new Date('2026-11-02T23:59:59.999Z'),
};

const ALERTA = Object.assign(new Alerta(), {
  id: 10,
  variavel: 'chuva_1h',
  territorio: 'RPA-1',
  nivel: 'ALTO',
  limiar: 50,
  valorLido: 62.5,
  lidaEm: new Date('2026-11-02T09:55:00Z'),
  status: StatusAlerta.Ativo,
  dthrDisparo: new Date('2026-11-02T10:00:00Z'),
});

const ACAO = Object.assign(new Acao(), {
  id: 7,
  descricao: 'Equipe enviada',
  idAlerta: 10,
  idUsuario: 2,
  usuario: Object.assign(new Usuario(), { id: 2, nome: 'Camila Rocha' }),
  dthrCriacao: new Date('2026-11-02T10:20:00Z'),
});

function setup() {
  const alertas = { find: jest.fn().mockResolvedValue([ALERTA]) };
  const acoes = { find: jest.fn().mockResolvedValue([ACAO]) };
  const service = new LinhaDoTempoService(
    alertas as unknown as Repository<Alerta>,
    acoes as unknown as Repository<Acao>,
  );
  return { service, alertas, acoes };
}

describe('LinhaDoTempoService (RN-005)', () => {
  it('reads alerts by trigger time and actions by registration time in the period', async () => {
    const { service, alertas, acoes } = setup();

    await service.consultar(PERIODO);

    expect(alertas.find).toHaveBeenCalledWith({
      where: { dthrDisparo: Between(PERIODO.inicio, PERIODO.fim) },
    });
    expect(acoes.find).toHaveBeenCalledWith({
      where: { dthrCriacao: Between(PERIODO.inicio, PERIODO.fim) },
      relations: { usuario: true },
    });
  });

  it('answers the period and the entries in the API shape', async () => {
    const { service } = setup();

    expect(await service.consultar(PERIODO)).toEqual({
      ...PERIODO,
      itens: [
        {
          tipo: 'ALERTA',
          em: new Date('2026-11-02T10:00:00Z'),
          alerta: {
            id: 10,
            variavel: 'chuva_1h',
            territorio: 'RPA-1',
            nivel: 'ALTO',
            limiar: 50,
            valor_lido: 62.5,
            lida_em: new Date('2026-11-02T09:55:00Z'),
            status: 'ATIVO',
          },
        },
        {
          tipo: 'ACAO',
          em: new Date('2026-11-02T10:20:00Z'),
          acao: {
            id: 7,
            descricao: 'Equipe enviada',
            id_alerta: 10,
            autor: { id: 2, nome: 'Camila Rocha' },
            registrada_em: new Date('2026-11-02T10:20:00Z'),
          },
        },
      ],
    });
  });
});
