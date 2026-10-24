import { INestApplication } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_PIPE } from '@nestjs/core';
import { JwtModule, JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { createValidationPipe } from '@/core/pipes/validation.pipe';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AuthGuard } from '@/modules/acesso/guards/auth.guard';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';
import { AlertaController } from '@/modules/alertas/controllers/alerta.controller';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { StatusAlerta } from '@/modules/alertas/enums/status-alerta.enum';
import { AlertaService } from '@/modules/alertas/services/alerta.service';

const PAPEIS: Papel[] = [
  Papel.Tecnico,
  Papel.Gestor,
  Papel.GestaoInstitucional,
  Papel.Comunicacao,
  Papel.Administrador,
];

const USUARIOS: Record<number, Usuario> = Object.fromEntries(
  PAPEIS.map((papel, i) => [
    i + 1,
    Object.assign(new Usuario(), {
      id: i + 1,
      nome: papel,
      ativo: true,
      papeis: [Object.assign(new UsuarioPapel(), { papel })],
    }),
  ]),
);

const ALERTA = Object.assign(new Alerta(), {
  id: 10,
  idParametroAlerta: 3,
  variavel: 'chuva_1h',
  territorio: 'RPA-1',
  limiar: 50,
  nivel: 'ALTO',
  fonte: 'APAC',
  estacao: 'REC-01',
  valorLido: 62.5,
  lidaEm: new Date('2026-10-24T10:00:00Z'),
  status: StatusAlerta.Ativo,
  dthrDisparo: new Date('2026-10-24T10:05:00Z'),
  dthrEncerramento: null,
});

// PER-006 and the MOD-002 contract, with the real guard, pipe and filter.
describe('AlertaController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = { listar: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [AlertaController],
      providers: [
        { provide: AlertaService, useValue: service },
        {
          provide: UsuarioService,
          useValue: {
            buscarAutenticado: (id: number) => Promise.resolve(USUARIOS[id]),
          },
        },
        { provide: APP_GUARD, useClass: AuthGuard },
        { provide: APP_PIPE, useFactory: createValidationPipe },
        { provide: APP_FILTER, useValue: new GlobalExceptionFilter(false) },
      ],
    }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
    const jwt = moduleRef.get(JwtService);
    for (const id of Object.keys(USUARIOS)) {
      tokens[Number(id)] = await jwt.signAsync({ sub: Number(id) });
    }
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    service.listar.mockReset();
    service.listar.mockResolvedValue({
      data: [ALERTA],
      meta: { itemsPerPage: 20, totalItems: 1, currentPage: 1, totalPages: 1 },
      links: { current: '/alertas?page=1' },
    });
  });

  const get = (id: number) =>
    request(app.getHttpServer())
      .get('/alertas')
      .set('Authorization', `Bearer ${tokens[id]}`);

  it('answers 401 without login', async () => {
    await request(app.getHttpServer()).get('/alertas').expect(401);
  });

  it.each([
    [1, 'TEC'],
    [2, 'GES'],
    [3, 'GIN'],
  ])('lists alerts for user %i (%s, PER-006)', async (id) => {
    await get(id).expect(200);
  });

  it.each([
    [4, 'COM (DUV-036, denied until answered)'],
    [5, 'ADM'],
  ])('answers 403 for user %i: %s (PER-006)', async (id) => {
    await get(id).expect(403);
    expect(service.listar).not.toHaveBeenCalled();
  });

  it('answers the MOD-002 contract without the update time of the source (RN-007 #2)', async () => {
    const response = await get(2).expect(200);

    expect((response.body as { data: unknown[] }).data).toEqual([
      {
        id: 10,
        nivel: 'ALTO',
        parametro: { id: 3, variavel: 'chuva_1h', limiar: 50 },
        territorio: 'RPA-1',
        valor_lido: 62.5,
        fonte: 'APAC',
        lida_em: '2026-10-24T10:00:00.000Z',
        disparado_em: '2026-10-24T10:05:00.000Z',
        fonte_atualizada_em: null,
        status: 'ATIVO',
      },
    ]);
  });
});
