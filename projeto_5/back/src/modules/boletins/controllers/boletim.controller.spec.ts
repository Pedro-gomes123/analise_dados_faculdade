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
import { BoletimController } from '@/modules/boletins/controllers/boletim.controller';
import { BoletimService } from '@/modules/boletins/services/boletim.service';

function usuario(id: number, papeis: Papel[]): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    ativo: true,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

const USUARIOS: Record<number, Usuario> = {
  1: usuario(1, [Papel.Tecnico]),
  2: usuario(2, [Papel.Comunicacao]),
  3: usuario(3, [Papel.Gestor]),
  4: usuario(4, [Papel.GestaoInstitucional]),
  5: usuario(5, [Papel.Administrador]),
};

const PREVIA = '/boletins/pre-visualizacao';
const PDF = '/boletins/pdf';

// PER-012 and RN-009 #2/#3, with the real guard, pipe and filter.
describe('BoletimController', () => {
  let app: INestApplication<App>;
  const tokens: Record<number, string> = {};
  const service = { preVisualizar: jest.fn(), gerarPdf: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [BoletimController],
      providers: [
        { provide: BoletimService, useValue: service },
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
    for (const id of [1, 2, 3, 4, 5]) {
      tokens[id] = await jwt.signAsync({ sub: id });
    }
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    service.preVisualizar.mockReset();
    service.gerarPdf.mockReset();
  });

  const post = (url: string, body: unknown, id: number) =>
    request(app.getHttpServer())
      .post(url)
      .set('Authorization', `Bearer ${tokens[id]}`)
      .send(body as object);

  it.each([PREVIA, PDF])('%s answers 401 without login', async (url) => {
    await request(app.getHttpServer())
      .post(url)
      .send({ secoes: ['rios'] })
      .expect(401);
  });

  it.each([1, 2])(
    'preview answers 200 with HTML for user %i (TEC, COM: PER-012)',
    async (id) => {
      service.preVisualizar.mockResolvedValue('<!doctype html><p>ok</p>');

      const res = await post(
        PREVIA,
        { secoes: ['rios', 'cabecalho'] },
        id,
      ).expect(200);

      expect(res.headers['content-type']).toBe('text/html; charset=utf-8');
      expect(res.text).toBe('<!doctype html><p>ok</p>');
      expect(service.preVisualizar).toHaveBeenCalledWith(['rios', 'cabecalho']);
    },
  );

  it.each([1, 2])(
    'pdf answers 200 with the file for user %i (TEC, COM: PER-012)',
    async (id) => {
      const conteudo = Buffer.from('%PDF-1.3 teste');
      service.gerarPdf.mockResolvedValue({
        nome: 'boletim-2026-11-02.pdf',
        conteudo,
      });

      const res = await post(PDF, { secoes: ['cabecalho'] }, id)
        .responseType('blob')
        .expect(200);

      expect(res.headers['content-type']).toBe('application/pdf');
      expect(res.headers['content-disposition']).toBe(
        'attachment; filename="boletim-2026-11-02.pdf"',
      );
      expect(res.body).toEqual(conteudo);
      expect(service.gerarPdf).toHaveBeenCalledWith(['cabecalho']);
    },
  );

  it.each([
    [PREVIA, 3],
    [PREVIA, 4],
    [PREVIA, 5],
    [PDF, 3],
    [PDF, 4],
    [PDF, 5],
  ])('%s answers 403 for user %i (GES, GIN, ADM)', async (url, id) => {
    await post(url, { secoes: ['rios'] }, id).expect(403);
    expect(service.preVisualizar).not.toHaveBeenCalled();
    expect(service.gerarPdf).not.toHaveBeenCalled();
  });

  it.each(
    [PREVIA, PDF].flatMap((url) => [
      [url, 'no section', { secoes: [] }],
      [url, 'an unknown section', { secoes: ['rios', 'abrigos'] }],
      [url, 'no field', {}],
      [url, 'not a list', { secoes: 'rios' }],
    ]),
  )('%s answers 422 in JSON for %s (RN-009 #2, #3)', async (url, _, body) => {
    const res = await post(url, body, 1)
      .expect(422)
      .expect('Content-Type', /application\/json/);
    const corpo = res.body as {
      message: string;
      errors: { property: string; constraints: Record<string, string> }[];
    };

    expect(corpo.message).toBe('Dados inválidos');
    expect(corpo.errors.map((e) => e.property)).toEqual(['secoes']);
    expect(Object.values(corpo.errors[0].constraints)).toContain(
      'Escolha ao menos uma seção válida',
    );
    expect(service.preVisualizar).not.toHaveBeenCalled();
    expect(service.gerarPdf).not.toHaveBeenCalled();
  });
});
