import { Controller, Get, INestApplication } from '@nestjs/common';
import { APP_FILTER, APP_GUARD } from '@nestjs/core';
import { JwtModule, JwtService } from '@nestjs/jwt';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { Public } from '@/core/auth/public.decorator';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { Papeis } from '@/modules/acesso/decorators/papeis.decorator';
import { UsuarioAtual } from '@/modules/acesso/decorators/usuario-atual.decorator';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import {
  AuthGuard,
  NAO_AUTENTICADO_MESSAGE,
  SEM_PERMISSAO_MESSAGE,
} from '@/modules/acesso/guards/auth.guard';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';

const SECRET = 'x'.repeat(32);

@Controller('teste')
class TesteController {
  @Public()
  @Get('publico')
  publico() {
    return 'ok';
  }

  @Get('logado')
  logado(@UsuarioAtual() usuario: Usuario) {
    return { id: usuario.id };
  }

  @Papeis(Papel.Gestor)
  @Get('gestor')
  gestor() {
    return 'ok';
  }
}

function usuario(papeis: Papel[], ativo = true): Usuario {
  return Object.assign(new Usuario(), {
    id: 5,
    ativo,
    papeis: papeis.map((papel) => Object.assign(new UsuarioPapel(), { papel })),
  });
}

describe('AuthGuard (DEC-013, PER)', () => {
  let app: INestApplication<App>;
  let jwt: JwtService;
  const usuarios = { buscarAutenticado: jest.fn() };

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      imports: [JwtModule.register({ secret: SECRET })],
      controllers: [TesteController],
      providers: [
        { provide: UsuarioService, useValue: usuarios },
        { provide: APP_GUARD, useClass: AuthGuard },
        { provide: APP_FILTER, useValue: new GlobalExceptionFilter(false) },
      ],
    }).compile();
    app = moduleRef.createNestApplication();
    await app.init();
    jwt = moduleRef.get(JwtService);
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(() => usuarios.buscarAutenticado.mockReset());

  const get = (path: string, token?: string) => {
    const req = request(app.getHttpServer()).get(path);
    return token ? req.set('Authorization', `Bearer ${token}`) : req;
  };
  const tokenDe = (sub: number) => jwt.signAsync({ sub });

  it('lets public routes through without a token', async () => {
    await get('/teste/publico').expect(200);
    expect(usuarios.buscarAutenticado).not.toHaveBeenCalled();
  });

  it('answers 401 without a token', async () => {
    const response = await get('/teste/logado').expect(401);
    expect((response.body as { message: string }).message).toBe(
      NAO_AUTENTICADO_MESSAGE,
    );
  });

  it('answers 401 for a token signed with another secret', async () => {
    const falso = await new JwtService({ secret: 'y'.repeat(32) }).signAsync({
      sub: 5,
    });
    await get('/teste/logado', falso).expect(401);
  });

  it('answers 401 for an expired token', async () => {
    const expirado = await jwt.signAsync({ sub: 5 }, { expiresIn: '-1s' });
    await get('/teste/logado', expirado).expect(401);
  });

  it('answers 401 when the user no longer exists or was deactivated', async () => {
    const token = await tokenDe(5);

    usuarios.buscarAutenticado.mockResolvedValue(null);
    await get('/teste/logado', token).expect(401);

    usuarios.buscarAutenticado.mockResolvedValue(
      usuario([Papel.Gestor], false),
    );
    await get('/teste/logado', token).expect(401);
  });

  it('loads the user from the database and exposes it to the route', async () => {
    usuarios.buscarAutenticado.mockResolvedValue(usuario([Papel.Tecnico]));

    const response = await get('/teste/logado', await tokenDe(5)).expect(200);

    expect(response.body).toEqual({ id: 5 });
    expect(usuarios.buscarAutenticado).toHaveBeenCalledWith(5);
  });

  it('answers 403 when the user lacks the required role', async () => {
    usuarios.buscarAutenticado.mockResolvedValue(usuario([Papel.Tecnico]));

    const response = await get('/teste/gestor', await tokenDe(5)).expect(403);
    expect((response.body as { message: string }).message).toBe(
      SEM_PERMISSAO_MESSAGE,
    );
  });

  it('lets a user with several roles through if any of them is allowed (AM-004 c)', async () => {
    usuarios.buscarAutenticado.mockResolvedValue(
      usuario([Papel.Tecnico, Papel.Gestor]),
    );

    await get('/teste/gestor', await tokenDe(5)).expect(200);
  });

  it('lets the administrator through any role check (PR-023)', async () => {
    usuarios.buscarAutenticado.mockResolvedValue(
      usuario([Papel.Administrador]),
    );

    await get('/teste/gestor', await tokenDe(5)).expect(200);
  });
});
