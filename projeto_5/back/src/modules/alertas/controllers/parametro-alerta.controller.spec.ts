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
import { ParametroAlertaController } from '@/modules/alertas/controllers/parametro-alerta.controller';
import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';
import { ParametroAlertaService } from '@/modules/alertas/services/parametro-alerta.service';

function usuario(id: number, papel: Papel): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    ativo: true,
    papeis: [Object.assign(new UsuarioPapel(), { papel })],
  });
}

const USUARIOS: Record<number, Usuario> = {
  1: usuario(1, Papel.Gestor),
  2: usuario(2, Papel.Tecnico),
  3: usuario(3, Papel.GestaoInstitucional),
};

const ATUALIZADO_EM = new Date('2026-10-24T10:00:00.000Z');

const PARAMETRO = Object.assign(new ParametroAlerta(), {
  id: 3,
  variavel: 'chuva_1h',
  territorio: 'RPA-1',
  limiar: 50,
  nivel: 'ALTO',
  ativo: true,
  dthrAtualizacao: ATUALIZADO_EM,
});

const pagina = <T>(data: T[]) => ({
  data,
  meta: {
    itemsPerPage: 20,
    totalItems: data.length,
    currentPage: 1,
    totalPages: 1,
  },
  links: { current: '?page=1' },
});

// PER-004, PER-005 and the HTTP contract, with the real guard, pipe and filter.
describe('ParametroAlertaController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = {
    listar: jest.fn(),
    historico: jest.fn(),
    criar: jest.fn(),
    alterar: jest.fn(),
  };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [ParametroAlertaController],
      providers: [
        { provide: ParametroAlertaService, useValue: service },
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
    for (const id of [1, 2, 3]) tokens[id] = await jwt.signAsync({ sub: id });
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    Object.values(service).forEach((fn) => fn.mockReset());
  });

  const auth = (id: number) => ({ Authorization: `Bearer ${tokens[id]}` });
  const valido = {
    variavel: 'chuva_1h',
    territorio: 'RPA-1',
    limiar: 50,
    nivel: 'ALTO',
  };

  describe('PER-004 (read)', () => {
    it.each([1, 2])('lists parameters for user %i (GES, TEC)', async (id) => {
      service.listar.mockResolvedValue(pagina([PARAMETRO]));

      const response = await request(app.getHttpServer())
        .get('/parametros-alerta')
        .set(auth(id))
        .expect(200);

      expect((response.body as { data: unknown[] }).data).toEqual([
        {
          id: 3,
          variavel: 'chuva_1h',
          territorio: 'RPA-1',
          limiar: 50,
          nivel: 'ALTO',
          ativo: true,
          atualizado_em: ATUALIZADO_EM.toISOString(),
        },
      ]);
    });

    it('answers 403 for GIN', async () => {
      await request(app.getHttpServer())
        .get('/parametros-alerta')
        .set(auth(3))
        .expect(403);
    });

    it('lists the history with author and values (RN-001)', async () => {
      service.historico.mockResolvedValue(
        pagina([
          Object.assign(new ParametroAlertaHistorico(), {
            id: 1,
            operacao: OperacaoHistorico.Alteracao,
            valorAnterior: { limiar: 50 },
            valorNovo: { limiar: 60 },
            usuario: USUARIOS[1],
            dthrCriacao: ATUALIZADO_EM,
          }),
        ]),
      );

      const response = await request(app.getHttpServer())
        .get('/parametros-alerta/3/historico')
        .set(auth(2))
        .expect(200);

      expect(service.historico).toHaveBeenCalledWith(3, expect.anything());
      expect((response.body as { data: unknown[] }).data).toEqual([
        {
          id: 1,
          operacao: 'ALTERACAO',
          valor_anterior: { limiar: 50 },
          valor_novo: { limiar: 60 },
          autor: { id: 1, nome: 'Usuário 1' },
          registrado_em: ATUALIZADO_EM.toISOString(),
        },
      ]);
    });
  });

  describe('PER-005 (write)', () => {
    it.each([2, 3])(
      'answers 403 on POST and PATCH for user %i (TEC, GIN)',
      async (id) => {
        await request(app.getHttpServer())
          .post('/parametros-alerta')
          .set(auth(id))
          .send(valido)
          .expect(403);
        await request(app.getHttpServer())
          .patch('/parametros-alerta/3')
          .set(auth(id))
          .send({ limiar: 60 })
          .expect(403);
        expect(service.criar).not.toHaveBeenCalled();
        expect(service.alterar).not.toHaveBeenCalled();
      },
    );

    it('creates with the logged user as author', async () => {
      service.criar.mockResolvedValue(PARAMETRO);

      await request(app.getHttpServer())
        .post('/parametros-alerta')
        .set(auth(1))
        .send({ ...valido, variavel: ' chuva_1h ' })
        .expect(201);

      expect(service.criar).toHaveBeenCalledWith(valido, USUARIOS[1]);
    });

    it('answers 422 for missing fields or more than 3 decimals', async () => {
      const response = await request(app.getHttpServer())
        .post('/parametros-alerta')
        .set(auth(1))
        .send({ limiar: 1.2345 })
        .expect(422);

      const body = response.body as { errors: { property: string }[] };
      expect(body.errors.map((e) => e.property).sort()).toEqual([
        'limiar',
        'nivel',
        'territorio',
        'variavel',
      ]);
    });

    it('does not let PATCH change variable or territory', async () => {
      await request(app.getHttpServer())
        .patch('/parametros-alerta/3')
        .set(auth(1))
        .send({ territorio: 'RPA-2' })
        .expect(422);
      expect(service.alterar).not.toHaveBeenCalled();
    });

    it('deactivates through PATCH (DEC-014)', async () => {
      service.alterar.mockResolvedValue({ ...PARAMETRO, ativo: false });

      await request(app.getHttpServer())
        .patch('/parametros-alerta/3')
        .set(auth(1))
        .send({ ativo: false })
        .expect(200);

      expect(service.alterar).toHaveBeenCalledWith(
        3,
        { ativo: false },
        USUARIOS[1],
      );
    });

    it('answers 422 for a non-numeric id and has no DELETE', async () => {
      await request(app.getHttpServer())
        .patch('/parametros-alerta/abc')
        .set(auth(1))
        .send({ limiar: 1 })
        .expect(422);
      await request(app.getHttpServer())
        .delete('/parametros-alerta/3')
        .set(auth(1))
        .expect(404);
    });
  });
});
