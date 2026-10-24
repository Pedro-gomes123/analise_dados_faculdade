import request from 'supertest';
import { DataSource } from 'typeorm';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { type AppE2e, criarAppE2e, limparBanco } from './helpers/e2e-app';
import { camposInvalidos, esperarErro } from './helpers/e2e-erro';
import { criarUsuario, entrar, SENHA } from './helpers/e2e-usuarios';

const LOGIN_INVALIDO = 'E-mail ou senha inválidos';
const NAO_AUTENTICADO = 'Faça login para continuar';

// FLX-001, PER-001, PER-002, RN-010 #5, RN-011, DEC-013, DEC-014.
describe('Auth (e2e)', () => {
  let app: AppE2e;

  beforeAll(async () => {
    app = await criarAppE2e();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await limparBanco(app);
  });

  const login = (email: string, senha: string) =>
    request(app.getHttpServer()).post('/auth/login').send({ email, senha });

  const me = (token?: string) => {
    const req = request(app.getHttpServer()).get('/auth/me');
    return token ? req.set('Authorization', `Bearer ${token}`) : req;
  };

  const registros = () =>
    app
      .get(DataSource)
      .getRepository(RegistroAcesso)
      .find({ order: { id: 'ASC' } });

  it('logs in with any letter case and /auth/me answers with the same user', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico, Papel.Gestor], {
      nome: 'Maria',
      email: 'maria@e2e.gov.br',
    });

    const res = await login('Maria@E2E.gov.br', SENHA).expect(200);
    const corpo = res.body as { access_token: string; usuario: unknown };

    const esperado = {
      id: usuario.id,
      nome: 'Maria',
      email: 'maria@e2e.gov.br',
      papeis: ['GES', 'TEC'],
      ativo: true,
    };
    expect(corpo.usuario).toEqual(esperado);
    expect(typeof corpo.access_token).toBe('string');

    const perfil = await me(corpo.access_token).expect(200);
    expect(perfil.body).toEqual(esperado);
  });

  it('records the successful attempt, never the password (RN-011 #1)', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico], {
      email: 'maria@e2e.gov.br',
    });

    await login('Maria@E2E.gov.br', SENHA).expect(200);

    expect(await registros()).toMatchObject([
      {
        emailInformado: 'Maria@E2E.gov.br',
        idUsuario: usuario.id,
        sucesso: true,
      },
    ]);
    const linhas: unknown = await app
      .get(DataSource)
      .query('SELECT * FROM [app].[registro_acesso]');
    expect(JSON.stringify(linhas)).not.toContain(SENHA);
  });

  it('wrong password: 401 with the generic message, attempt recorded', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico]);

    esperarErro(await login(usuario.email, 'senha-errada-1'), {
      status: 401,
      message: LOGIN_INVALIDO,
    });

    expect(await registros()).toMatchObject([
      { idUsuario: usuario.id, sucesso: false },
    ]);
  });

  it('unknown e-mail: the same 401, attempt recorded without a user', async () => {
    esperarErro(await login('ninguem@e2e.gov.br', SENHA), {
      status: 401,
      message: LOGIN_INVALIDO,
    });

    expect(await registros()).toMatchObject([
      { emailInformado: 'ninguem@e2e.gov.br', idUsuario: null, sucesso: false },
    ]);
  });

  it('inactive user cannot log in, even with the right password (RN-010 #5)', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico], { ativo: false });

    esperarErro(await login(usuario.email, SENHA), {
      status: 401,
      message: LOGIN_INVALIDO,
    });
    expect(await registros()).toMatchObject([
      { idUsuario: usuario.id, sucesso: false },
    ]);
  });

  it('a token stops working as soon as the user is deactivated (DEC-014)', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico]);
    const token = await entrar(app, usuario.email);
    await me(token).expect(200);

    await app
      .get(DataSource)
      .getRepository(Usuario)
      .update(usuario.id, { ativo: false });

    esperarErro(await me(token), { status: 401, message: NAO_AUTENTICADO });
  });

  it('/auth/me without a token or with an invalid one: 401 (PER-002)', async () => {
    esperarErro(await me(), { status: 401, message: NAO_AUTENTICADO });
    esperarErro(await me('nao-e-um-jwt'), {
      status: 401,
      message: NAO_AUTENTICADO,
    });
  });

  it('invalid body: 422 and no attempt recorded', async () => {
    const res = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: 'nao-e-email' });

    expect(camposInvalidos(res)).toEqual(['email', 'senha']);
    expect(await registros()).toEqual([]);
  });
});
