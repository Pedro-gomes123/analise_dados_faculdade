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
import { LinhaDoTempoController } from '@/modules/rastreio-operacional/controllers/linha-do-tempo.controller';
import { LinhaDoTempoService } from '@/modules/rastreio-operacional/services/linha-do-tempo.service';

function usuario(id: number, papeis: Papel[]): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    ativo: true,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

const USUARIOS: Record<number, Usuario> = {
  1: usuario(1, [Papel.Gestor]),
  2: usuario(2, [Papel.GestaoInstitucional]),
  3: usuario(3, [Papel.Comunicacao]),
};

const URL =
  '/linha-do-tempo?inicio=2026-11-02T00:00:00Z&fim=2026-11-02T23:59:59Z';

// PER-008 and the period validation, with the real guard, pipe and filter.
describe('LinhaDoTempoController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = { consultar: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [LinhaDoTempoController],
      providers: [
        { provide: LinhaDoTempoService, useValue: service },
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
    service.consultar.mockReset();
  });

  const get = (url: string, id: number) =>
    request(app.getHttpServer())
      .get(url)
      .set('Authorization', `Bearer ${tokens[id]}`);

  it('answers 401 without login', async () => {
    await request(app.getHttpServer()).get(URL).expect(401);
  });

  it.each([1, 2])('answers 200 for user %i (GES, GIN: PER-008)', async (id) => {
    service.consultar.mockResolvedValue({ itens: [] });

    await get(URL, id).expect(200);

    expect(service.consultar).toHaveBeenCalledWith({
      inicio: new Date('2026-11-02T00:00:00Z'),
      fim: new Date('2026-11-02T23:59:59Z'),
    });
  });

  it('answers 403 for COM (PER-008)', async () => {
    await get(URL, 3).expect(403);
    expect(service.consultar).not.toHaveBeenCalled();
  });

  it('answers 422 without a valid period', async () => {
    await get('/linha-do-tempo', 1).expect(422);
    await get(
      '/linha-do-tempo?inicio=2026-11-03T00:00:00Z&fim=2026-11-02T00:00:00Z',
      1,
    ).expect(422);
    expect(service.consultar).not.toHaveBeenCalled();
  });
});
