import { HttpStatus, INestApplication } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_PIPE } from '@nestjs/core';
import { JwtModule, JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { BusinessRuleException } from '@/core/exceptions/business-rule.exception';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { createValidationPipe } from '@/core/pipes/validation.pipe';
import { AcessoRules } from '@/modules/acesso/acesso.business-rules';
import { UsuarioController } from '@/modules/acesso/controllers/usuario.controller';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { AuthGuard } from '@/modules/acesso/guards/auth.guard';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';

function usuario(id: number, papeis: Papel[]): Usuario {
  return Object.assign(new Usuario(), {
    id,
    nome: `Usuário ${id}`,
    email: `u${id}@exemplo.gov.br`,
    senhaHash: 'nao-pode-sair',
    ativo: true,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

const ADMIN = usuario(1, [Papel.Administrador]);
const GESTOR = usuario(2, [Papel.Gestor]);

// PER-003 and the HTTP contract of /usuarios, with the real guard, pipe and filter.
describe('UsuarioController', () => {
  let app: INestApplication<App>;
  let tokenAdmin: string;
  let tokenGestor: string;
  const service = {
    buscarAutenticado: jest.fn((id: number) =>
      Promise.resolve(id === 1 ? ADMIN : GESTOR),
    ),
    listar: jest.fn(),
    buscarPorId: jest.fn(),
    criar: jest.fn(),
    alterar: jest.fn(),
  };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: 'x'.repeat(32) })],
      controllers: [UsuarioController],
      providers: [
        { provide: UsuarioService, useValue: service },
        { provide: APP_GUARD, useClass: AuthGuard },
        { provide: APP_PIPE, useFactory: createValidationPipe },
        { provide: APP_FILTER, useValue: new GlobalExceptionFilter(false) },
      ],
    }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
    const jwt = moduleRef.get(JwtService);
    tokenAdmin = await jwt.signAsync({ sub: 1 });
    tokenGestor = await jwt.signAsync({ sub: 2 });
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => {
    service.listar.mockReset();
    service.criar.mockReset();
    service.alterar.mockReset();
  });

  const valido = {
    nome: 'Marcos Andrade',
    email: 'marcos@exemplo.gov.br',
    senha: 'Senha-forte-1',
    papeis: [Papel.Tecnico],
  };

  describe('PER-003', () => {
    it('answers 401 without login', async () => {
      await request(app.getHttpServer()).get('/usuarios').expect(401);
    });

    it('answers 403 for a non-administrator', async () => {
      await request(app.getHttpServer())
        .post('/usuarios')
        .set('Authorization', `Bearer ${tokenGestor}`)
        .send(valido)
        .expect(403);
      expect(service.criar).not.toHaveBeenCalled();
    });
  });

  it('POST creates a user and answers 201 without the password hash', async () => {
    service.criar.mockResolvedValue(usuario(9, [Papel.Tecnico]));

    const response = await request(app.getHttpServer())
      .post('/usuarios')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send(valido)
      .expect(201);

    expect(response.body).toEqual({
      id: 9,
      nome: 'Usuário 9',
      email: 'u9@exemplo.gov.br',
      papeis: [Papel.Tecnico],
      ativo: true,
    });
    expect(JSON.stringify(response.body)).not.toContain('nao-pode-sair');
  });

  it('POST answers 422 for missing roles, an unknown role or a short password', async () => {
    const response = await request(app.getHttpServer())
      .post('/usuarios')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send({ ...valido, senha: 'curta', papeis: ['XYZ'] })
      .expect(422);

    const body = response.body as { errors: { property: string }[] };
    expect(body.errors.map((e) => e.property).sort()).toEqual([
      'papeis',
      'senha',
    ]);

    await request(app.getHttpServer())
      .post('/usuarios')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send({ ...valido, papeis: [] })
      .expect(422);
  });

  it('POST answers 409 EMAIL_JA_CADASTRADO from the service', async () => {
    service.criar.mockRejectedValue(
      new BusinessRuleException(AcessoRules.EMAIL_JA_CADASTRADO),
    );

    const response = await request(app.getHttpServer())
      .post('/usuarios')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send(valido)
      .expect(HttpStatus.CONFLICT);

    expect(response.body).toMatchObject({
      business_rule_code: 'EMAIL_JA_CADASTRADO',
    });
  });

  it('PATCH does not accept changing the e-mail', async () => {
    await request(app.getHttpServer())
      .patch('/usuarios/9')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send({ email: 'novo@exemplo.gov.br' })
      .expect(422);
    expect(service.alterar).not.toHaveBeenCalled();
  });

  it('PATCH deactivates a user', async () => {
    service.alterar.mockResolvedValue(
      Object.assign(usuario(9, [Papel.Tecnico]), { ativo: false }),
    );

    const response = await request(app.getHttpServer())
      .patch('/usuarios/9')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .send({ ativo: false })
      .expect(200);

    expect(service.alterar).toHaveBeenCalledWith(9, { ativo: false });
    expect(response.body).toMatchObject({ id: 9, ativo: false });
  });

  it('answers 422 for a non-numeric id', async () => {
    await request(app.getHttpServer())
      .get('/usuarios/abc')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .expect(422);
  });

  it('GET maps the page to the public user shape', async () => {
    service.listar.mockResolvedValue({
      data: [usuario(9, [Papel.Tecnico])],
      meta: { totalItems: 1 },
      links: { current: '/usuarios?page=1' },
    });

    const response = await request(app.getHttpServer())
      .get('/usuarios?search=marcos')
      .set('Authorization', `Bearer ${tokenAdmin}`)
      .expect(200);

    const body = response.body as { data: unknown[]; meta: unknown };
    expect(body.data).toEqual([
      expect.objectContaining({ id: 9, papeis: [Papel.Tecnico] }),
    ]);
    expect(body.meta).toEqual({ totalItems: 1 });
    expect(JSON.stringify(body)).not.toContain('nao-pode-sair');
  });
});
