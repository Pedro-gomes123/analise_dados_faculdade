import { INestApplication, NotFoundException } from '@nestjs/common';
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
import { AcaoController } from '@/modules/rastreio-operacional/controllers/acao.controller';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { AcaoService } from '@/modules/rastreio-operacional/services/acao.service';

function usuario(id: number, papeis: Papel[]): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    email: `u${id}@exemplo.gov.br`,
    ativo: true,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

const USUARIOS: Record<number, Usuario> = {
  1: usuario(1, [Papel.Gestor]),
  2: usuario(2, [Papel.GestaoInstitucional]),
  3: usuario(3, [Papel.Tecnico]),
};

const REGISTRADA_EM = new Date('2026-10-24T10:20:00.000Z');

function acao(id: number, idAlerta: number | null): Acao {
  return Object.assign(new Acao(), {
    id,
    descricao: 'Equipe de vigilância enviada ao território',
    idAlerta,
    idUsuario: 1,
    usuario: USUARIOS[1],
    dthrCriacao: REGISTRADA_EM,
  });
}

// PER-007, PER-008 and the MOD-003 contract, with the real guard, pipe and filter.
describe('AcaoController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = { criar: jest.fn(), listar: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [AcaoController],
      providers: [
        { provide: AcaoService, useValue: service },
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
    service.criar.mockReset();
    service.listar.mockReset();
  });

  const post = (token: string, body: object) =>
    request(app.getHttpServer())
      .post('/acoes')
      .set('Authorization', `Bearer ${token}`)
      .send(body);

  describe('POST /acoes', () => {
    it('answers 401 without login', async () => {
      await request(app.getHttpServer()).post('/acoes').expect(401);
    });

    it.each([
      [2, 'GIN (DUV-036, denied until answered)'],
      [3, 'TEC'],
    ])('answers 403 for user %i: %s (PER-007)', async (id) => {
      await post(tokens[id], { descricao: 'x' }).expect(403);
      expect(service.criar).not.toHaveBeenCalled();
    });

    it('creates the action with the logged user and answers the contract', async () => {
      service.criar.mockResolvedValue(acao(7, 10));

      const response = await post(tokens[1], {
        descricao: '  Equipe de vigilância enviada ao território ',
        id_alerta: 10,
      }).expect(201);

      expect(service.criar).toHaveBeenCalledWith(
        {
          descricao: 'Equipe de vigilância enviada ao território',
          idAlerta: 10,
        },
        USUARIOS[1],
      );
      expect(response.body).toEqual({
        id: 7,
        descricao: 'Equipe de vigilância enviada ao território',
        id_alerta: 10,
        autor: { id: 1, nome: 'Usuário 1' },
        registrada_em: REGISTRADA_EM.toISOString(),
      });
    });

    it('answers 422 for an empty description (RN-004 #2)', async () => {
      const response = await post(tokens[1], { descricao: '   ' }).expect(422);

      const body = response.body as {
        errors: { property: string; constraints: Record<string, string> }[];
      };
      expect(body.errors[0]).toMatchObject({
        property: 'descricao',
        constraints: { isNotEmpty: 'Descreva a ação' },
      });
    });

    it('answers 422 when the client sends author or time (RN-004 #3)', async () => {
      await post(tokens[1], { descricao: 'x', id_usuario: 9 }).expect(422);
      await post(tokens[1], {
        descricao: 'x',
        registrada_em: '2020-01-01T00:00:00Z',
      }).expect(422);
      expect(service.criar).not.toHaveBeenCalled();
    });

    it('answers 422 for an invalid alert id', async () => {
      await post(tokens[1], { descricao: 'x', id_alerta: 'dez' }).expect(422);
      await post(tokens[1], { descricao: 'x', id_alerta: 0 }).expect(422);
    });

    it('answers 404 when the alert does not exist', async () => {
      service.criar.mockRejectedValue(
        new NotFoundException('Alerta não encontrado'),
      );

      await post(tokens[1], { descricao: 'x', id_alerta: 99 }).expect(404);
    });
  });

  describe('GET /acoes', () => {
    const pagina = {
      data: [acao(7, null)],
      meta: { itemsPerPage: 20, totalItems: 1, currentPage: 1, totalPages: 1 },
      links: { current: '/acoes?page=1' },
    };

    it.each([1, 2])(
      'lists actions for user %i (GES, GIN: PER-008)',
      async (id) => {
        service.listar.mockResolvedValue(pagina);

        const response = await request(app.getHttpServer())
          .get('/acoes')
          .set('Authorization', `Bearer ${tokens[id]}`)
          .expect(200);

        expect((response.body as { data: unknown[] }).data).toEqual([
          {
            id: 7,
            descricao: 'Equipe de vigilância enviada ao território',
            id_alerta: null,
            autor: { id: 1, nome: 'Usuário 1' },
            registrada_em: REGISTRADA_EM.toISOString(),
          },
        ]);
      },
    );

    it('answers 403 for TEC (PER-008)', async () => {
      await request(app.getHttpServer())
        .get('/acoes')
        .set('Authorization', `Bearer ${tokens[3]}`)
        .expect(403);
    });
  });

  it('has no route to edit or delete an action (RN-004 #5)', async () => {
    await request(app.getHttpServer())
      .patch('/acoes/7')
      .set('Authorization', `Bearer ${tokens[1]}`)
      .send({ descricao: 'y' })
      .expect(404);
    await request(app.getHttpServer())
      .delete('/acoes/7')
      .set('Authorization', `Bearer ${tokens[1]}`)
      .expect(404);
  });
});
