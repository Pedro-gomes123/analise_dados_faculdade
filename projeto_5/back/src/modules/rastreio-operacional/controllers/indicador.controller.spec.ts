import { INestApplication } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_PIPE } from '@nestjs/core';
import { JwtModule, JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { PERIODO_INVERTIDO_MESSAGE } from '@/core/dto/periodo-query.dto';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { createValidationPipe } from '@/core/pipes/validation.pipe';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AuthGuard } from '@/modules/acesso/guards/auth.guard';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';
import { IndicadorController } from '@/modules/rastreio-operacional/controllers/indicador.controller';
import { TempoAcionamentoService } from '@/modules/rastreio-operacional/services/tempo-acionamento.service';

function usuario(id: number, papeis: Papel[]): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    ativo: true,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

const USUARIOS: Record<number, Usuario> = {
  1: usuario(1, [Papel.GestaoInstitucional]),
  2: usuario(2, [Papel.Gestor]),
};

const URL =
  '/indicadores/tempo-acionamento?inicio=2026-11-01T00:00:00Z&fim=2026-11-07T23:59:59Z';

// PER-009 and the period validation, with the real guard, pipe and filter.
describe('IndicadorController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = { calcular: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [IndicadorController],
      providers: [
        { provide: TempoAcionamentoService, useValue: service },
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
    for (const id of [1, 2]) tokens[id] = await jwt.signAsync({ sub: id });
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    service.calcular.mockReset();
  });

  const get = (url: string, id = 1) =>
    request(app.getHttpServer())
      .get(url)
      .set('Authorization', `Bearer ${tokens[id]}`);

  it('answers 401 without login', async () => {
    await request(app.getHttpServer()).get(URL).expect(401);
  });

  it('answers 403 for GES (PER-009: GIN only)', async () => {
    await get(URL, 2).expect(403);
    expect(service.calcular).not.toHaveBeenCalled();
  });

  it('passes the period as dates to the service', async () => {
    service.calcular.mockResolvedValue({ media_segundos: 600 });

    const response = await get(URL).expect(200);

    expect(service.calcular).toHaveBeenCalledWith({
      inicio: new Date('2026-11-01T00:00:00Z'),
      fim: new Date('2026-11-07T23:59:59Z'),
    });
    expect(response.body).toEqual({ media_segundos: 600 });
  });

  it('answers 422 without the period or with an invalid date', async () => {
    await get('/indicadores/tempo-acionamento').expect(422);
    await get(
      '/indicadores/tempo-acionamento?inicio=ontem&fim=2026-11-07T00:00:00Z',
    ).expect(422);
    expect(service.calcular).not.toHaveBeenCalled();
  });

  it('answers 422 when the period is inverted', async () => {
    const response = await get(
      '/indicadores/tempo-acionamento?inicio=2026-11-07T00:00:00Z&fim=2026-11-01T00:00:00Z',
    ).expect(422);

    expect((response.body as { message: string }).message).toBe(
      PERIODO_INVERTIDO_MESSAGE,
    );
    expect(service.calcular).not.toHaveBeenCalled();
  });
});
