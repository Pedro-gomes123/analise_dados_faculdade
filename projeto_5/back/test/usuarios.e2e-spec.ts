import request from 'supertest';
import { DataSource } from 'typeorm';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { type AppE2e, criarAppE2e, limparBanco } from './helpers/e2e-app';
import { camposInvalidos, esperarErro } from './helpers/e2e-erro';
import { criarUsuario, entrar, logado } from './helpers/e2e-usuarios';

interface UsuarioApi {
  id: number;
  nome: string;
  email: string;
  papeis: string[];
  ativo: boolean;
}

const NOVO = {
  nome: '  Ana Souza  ',
  email: 'Ana@E2E.gov.br',
  senha: 'inicial-123',
  papeis: ['TEC', 'GES', 'TEC'],
};

// PER-003, RN-010, PR-020, DEC-012, DEC-014.
describe('Usuários (e2e)', () => {
  let app: AppE2e;
  let token: string;

  beforeAll(async () => {
    app = await criarAppE2e();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await limparBanco(app);
    ({ token } = await logado(app, [Papel.Administrador]));
  });

  const http = () => request(app.getHttpServer());
  const auth = (t = token) => ({ Authorization: `Bearer ${t}` });
  const criar = (corpo: object, t = token) =>
    http().post('/usuarios').set(auth(t)).send(corpo);

  it('ADM creates an active user who logs in with the initial password (RN-010 #1, PR-020)', async () => {
    const res = await criar(NOVO).expect(201);
    const criado = res.body as UsuarioApi;

    expect(criado).toEqual({
      id: expect.any(Number) as number,
      nome: 'Ana Souza',
      email: 'ana@e2e.gov.br',
      papeis: ['GES', 'TEC'],
      ativo: true,
    });
    expect(res.body).not.toHaveProperty('senha_hash');
    expect(
      await app
        .get(DataSource)
        .getRepository(UsuarioPapel)
        .countBy({ idUsuario: criado.id }),
    ).toBe(2);

    await entrar(app, 'ana@e2e.gov.br', 'inicial-123');
  });

  it('e-mail already registered, even inactive and in another case: 409 (RN-010 #2)', async () => {
    await criarUsuario(app, [Papel.Tecnico], {
      email: 'ana@e2e.gov.br',
      ativo: false,
    });

    esperarErro(await criar(NOVO), {
      status: 409,
      businessRuleCode: 'EMAIL_JA_CADASTRADO',
      message: 'Já existe um usuário com este e-mail',
    });
  });

  it('two simultaneous creations with the same e-mail: one 201, one 409 (RN-010 concurrency)', async () => {
    const respostas = await Promise.all([criar(NOVO), criar(NOVO)]);

    expect(respostas.map((r) => r.status).sort()).toEqual([201, 409]);
    esperarErro(
      respostas.find((r) => r.status === 409)!,
      {
        status: 409,
        businessRuleCode: 'EMAIL_JA_CADASTRADO',
      },
    );
    expect(
      await app
        .get(DataSource)
        .getRepository(Usuario)
        .countBy({ email: 'ana@e2e.gov.br' }),
    ).toBe(1);
  });

  it('user without a role or with an unknown role: 422 (RN-010 #3)', async () => {
    expect(camposInvalidos(await criar({ ...NOVO, papeis: [] }))).toEqual([
      'papeis',
    ]);
    expect(camposInvalidos(await criar({ ...NOVO, papeis: ['XYZ'] }))).toEqual([
      'papeis',
    ]);
  });

  it.each([
    Papel.Tecnico,
    Papel.Gestor,
    Papel.GestaoInstitucional,
    Papel.Comunicacao,
  ])(
    '%s cannot create nor list users: 403 (RN-010 #4, PER-003)',
    async (papel) => {
      const outro = await logado(app, [papel]);

      esperarErro(await criar(NOVO, outro.token), { status: 403 });
      esperarErro(await http().get('/usuarios').set(auth(outro.token)), {
        status: 403,
      });
    },
  );

  it('without login: 401', async () => {
    esperarErro(await http().get('/usuarios'), { status: 401 });
  });

  it('lists with search and pagination, never the password hash (DEC-012)', async () => {
    await criarUsuario(app, [Papel.Tecnico], { nome: 'Ana Souza' });
    await criarUsuario(app, [Papel.Gestor], { nome: 'Bruno Lima' });

    const res = await http()
      .get('/usuarios?search=ana&limit=1')
      .set(auth())
      .expect(200);
    const pagina = res.body as {
      data: UsuarioApi[];
      meta: { totalItems: number; itemsPerPage: number };
    };

    expect(pagina.data.map((u) => u.nome)).toEqual(['Ana Souza']);
    expect(pagina.meta).toMatchObject({ totalItems: 1, itemsPerPage: 1 });
    expect(JSON.stringify(pagina)).not.toContain('senha');
  });

  it('deactivates without deleting: login is refused and the user is still there (DEC-014)', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico]);

    const res = await http()
      .patch(`/usuarios/${usuario.id}`)
      .set(auth())
      .send({ ativo: false })
      .expect(200);
    expect((res.body as UsuarioApi).ativo).toBe(false);

    esperarErro(
      await http()
        .post('/auth/login')
        .send({ email: usuario.email, senha: 'senha-e2e-123' }),
      { status: 401 },
    );
    await http().get(`/usuarios/${usuario.id}`).set(auth()).expect(200);
  });

  it('changes roles and resets the password; the old password stops working (PR-020)', async () => {
    const usuario = await criarUsuario(app, [Papel.Tecnico, Papel.Gestor]);

    const res = await http()
      .patch(`/usuarios/${usuario.id}`)
      .set(auth())
      .send({ papeis: ['COM'], senha: 'nova-senha-123' })
      .expect(200);
    expect((res.body as UsuarioApi).papeis).toEqual(['COM']);

    esperarErro(
      await http()
        .post('/auth/login')
        .send({ email: usuario.email, senha: 'senha-e2e-123' }),
      { status: 401 },
    );
    await entrar(app, usuario.email, 'nova-senha-123');
  });

  it('unknown id: 404; id that is not a number: 422', async () => {
    esperarErro(await http().get('/usuarios/999999').set(auth()), {
      status: 404,
      message: 'Usuário não encontrado',
    });
    esperarErro(await http().get('/usuarios/abc').set(auth()), {
      status: 422,
    });
  });
});
