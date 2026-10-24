import { INestApplication, UnauthorizedException } from '@nestjs/common';
import { APP_FILTER, APP_PIPE } from '@nestjs/core';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { createValidationPipe } from '@/core/pipes/validation.pipe';
import { AuthController } from '@/modules/acesso/controllers/auth.controller';
import { AuthService } from '@/modules/acesso/services/auth.service';

// HTTP contract of POST /auth/login with the real pipe and filter; the service is mocked.
describe('AuthController', () => {
  let app: INestApplication<App>;
  const auth = { login: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      controllers: [AuthController],
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: APP_PIPE, useFactory: createValidationPipe },
        { provide: APP_FILTER, useValue: new GlobalExceptionFilter(false) },
      ],
    }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => auth.login.mockReset());

  it('answers 200 with the token', async () => {
    auth.login.mockResolvedValue({ access_token: 'jwt', usuario: { id: 1 } });

    const response = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: 'a@b.com', senha: 'x' })
      .expect(200);

    expect(response.body).toEqual({ access_token: 'jwt', usuario: { id: 1 } });
    expect(auth.login).toHaveBeenCalledWith('a@b.com', 'x');
  });

  it('answers 401 in the error contract when the service refuses', async () => {
    auth.login.mockRejectedValue(
      new UnauthorizedException('E-mail ou senha inválidos'),
    );

    const response = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: 'a@b.com', senha: 'x' })
      .expect(401);

    expect(response.body).toMatchObject({
      status_code: 401,
      message: 'E-mail ou senha inválidos',
      path: '/auth/login',
    });
  });

  it('answers 422 for an invalid e-mail, a missing password or an extra field', async () => {
    const response = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: 'nao-e-email', papel: 'ADM' })
      .expect(422);

    const body = response.body as { errors: { property: string }[] };
    expect(body.errors.map((e) => e.property).sort()).toEqual([
      'email',
      'papel',
      'senha',
    ]);
    expect(auth.login).not.toHaveBeenCalled();
  });
});
