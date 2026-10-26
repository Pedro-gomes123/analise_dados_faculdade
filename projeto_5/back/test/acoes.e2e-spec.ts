import request from 'supertest';
import { DataSource } from 'typeorm';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import { criarAlerta, registrarAcaoEm } from './helpers/e2e-alertas';
import { type AppE2e, criarAppE2e, limparBanco } from './helpers/e2e-app';
import { camposInvalidos, esperarErro } from './helpers/e2e-erro';
import { logado } from './helpers/e2e-usuarios';

interface AcaoApi {
  id: number;
  descricao: string;
  id_alerta: number | null;
  autor: { id: number; nome: string };
  registrada_em: string;
}

interface ItemApi {
  tipo: 'ALERTA' | 'ACAO';
  em: string;
  alerta?: { id: number };
  acao?: { id: number; descricao: string };
}

// Server and database clocks may differ a little (Docker on WSL).
const TOLERANCIA_MS = 5 * 60_000;

// PER-007, PER-008, RN-004, RN-005, DEC-014.
describe('Ações e linha do tempo (e2e)', () => {
  let app: AppE2e;
  let gestor: Awaited<ReturnType<typeof logado>>;

  beforeAll(async () => {
    app = await criarAppE2e();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await limparBanco(app);
    gestor = await logado(app, [Papel.Gestor]);
  });

  const http = () => request(app.getHttpServer());
  const auth = (token = gestor.token) => ({
    Authorization: `Bearer ${token}`,
  });
  const registrar = (corpo: object, token?: string) =>
    http().post('/acoes').set(auth(token)).send(corpo);
  const acoesNoBanco = () =>
    app
      .get(DataSource)
      .getRepository(Acao)
      .find({ order: { id: 'ASC' } });

  describe('registro (RN-004)', () => {
    it('records the authenticated author and the server time (RN-004 #1)', async () => {
      const antes = Date.now();
      const res = await registrar({ descricao: '  Equipe enviada  ' }).expect(
        201,
      );
      const acao = res.body as AcaoApi;

      expect(acao).toMatchObject({
        descricao: 'Equipe enviada',
        id_alerta: null,
        autor: { id: gestor.usuario.id, nome: gestor.usuario.nome },
      });
      const registradaEm = Date.parse(acao.registrada_em);
      expect(Math.abs(registradaEm - antes)).toBeLessThan(TOLERANCIA_MS);
      expect(await acoesNoBanco()).toMatchObject([
        { id: acao.id, idUsuario: gestor.usuario.id, idAlerta: null },
      ]);
    });

    it('links the action to an alert (RN-004 #4)', async () => {
      const alerta = await criarAlerta(app, { disparadoEm: new Date() });

      const res = await registrar({
        descricao: 'Abrigo aberto',
        id_alerta: alerta.id,
      }).expect(201);

      expect((res.body as AcaoApi).id_alerta).toBe(alerta.id);
      expect(await acoesNoBanco()).toMatchObject([{ idAlerta: alerta.id }]);
    });

    it('unknown alert: 404 and nothing recorded', async () => {
      esperarErro(await registrar({ descricao: 'X', id_alerta: 999999 }), {
        status: 404,
        message: 'Alerta não encontrado',
      });
      expect(await acoesNoBanco()).toEqual([]);
    });

    it('empty description: 422 (RN-004 #2)', async () => {
      expect(camposInvalidos(await registrar({ descricao: '   ' }))).toEqual([
        'descricao',
      ]);
    });

    it('author or time sent by the client: refused (RN-004 #3)', async () => {
      const res = await registrar({
        descricao: 'Equipe enviada',
        id_usuario: 999,
        registrada_em: '2020-01-01T00:00:00Z',
      });

      expect(camposInvalidos(res).sort()).toEqual([
        'id_usuario',
        'registrada_em',
      ]);
      expect(await acoesNoBanco()).toEqual([]);
    });

    it('there is no way to edit or delete an action (RN-004 #5, DEC-014)', async () => {
      const { id } = (await registrar({ descricao: 'Original' }).expect(201))
        .body as AcaoApi;

      esperarErro(
        await http()
          .patch(`/acoes/${id}`)
          .set(auth())
          .send({ descricao: 'Alterada' }),
        { status: 404 },
      );
      esperarErro(await http().delete(`/acoes/${id}`).set(auth()), {
        status: 404,
      });
      expect(await acoesNoBanco()).toMatchObject([{ descricao: 'Original' }]);
    });

    it.each([Papel.GestaoInstitucional, Papel.Tecnico, Papel.Comunicacao])(
      '%s cannot register: 403 (PER-007)',
      async (papel) => {
        const outro = await logado(app, [papel]);
        esperarErro(await registrar({ descricao: 'X' }, outro.token), {
          status: 403,
        });
      },
    );

    it('GES and GIN list the actions, newest first; TEC and COM cannot (PER-008)', async () => {
      await registrarAcaoEm(app, {
        descricao: 'Primeira',
        idUsuario: gestor.usuario.id,
        registradaEm: new Date('2026-11-02T10:00:00Z'),
      });
      await registrarAcaoEm(app, {
        descricao: 'Segunda',
        idUsuario: gestor.usuario.id,
        registradaEm: new Date('2026-11-02T11:00:00Z'),
      });
      const gin = await logado(app, [Papel.GestaoInstitucional]);

      for (const token of [gestor.token, gin.token]) {
        const res = await http().get('/acoes').set(auth(token)).expect(200);
        const { data } = res.body as { data: AcaoApi[] };
        expect(data.map((a) => a.descricao)).toEqual(['Segunda', 'Primeira']);
      }
      for (const papel of [Papel.Tecnico, Papel.Comunicacao]) {
        const outro = await logado(app, [papel]);
        esperarErro(await http().get('/acoes').set(auth(outro.token)), {
          status: 403,
        });
      }
    });
  });

  describe('linha do tempo (RN-005)', () => {
    const PERIODO =
      '/linha-do-tempo?inicio=2026-11-02T00:00:00Z&fim=2026-11-02T23:59:59Z';

    it('alerts and actions of the period in chronological order', async () => {
      const alerta = await criarAlerta(app, {
        disparadoEm: new Date('2026-11-02T10:00:00Z'),
      });
      await criarAlerta(app, {
        disparadoEm: new Date('2026-11-03T10:00:00Z'),
      });
      await registrarAcaoEm(app, {
        descricao: 'Resposta',
        idUsuario: gestor.usuario.id,
        idAlerta: alerta.id,
        registradaEm: new Date('2026-11-02T10:20:00Z'),
      });
      await registrarAcaoEm(app, {
        descricao: 'Preparação',
        idUsuario: gestor.usuario.id,
        registradaEm: new Date('2026-11-02T09:00:00Z'),
      });
      await registrarAcaoEm(app, {
        descricao: 'Fora do período',
        idUsuario: gestor.usuario.id,
        registradaEm: new Date('2026-11-01T23:59:59Z'),
      });

      const res = await http().get(PERIODO).set(auth()).expect(200);
      const { itens } = res.body as { itens: ItemApi[] };

      expect(
        itens.map((i) => [i.tipo, i.em, i.acao?.descricao ?? i.alerta?.id]),
      ).toEqual([
        ['ACAO', '2026-11-02T09:00:00.000Z', 'Preparação'],
        ['ALERTA', '2026-11-02T10:00:00.000Z', alerta.id],
        ['ACAO', '2026-11-02T10:20:00.000Z', 'Resposta'],
      ]);
    });

    it('GIN reads it; TEC and COM cannot (PER-008)', async () => {
      const gin = await logado(app, [Papel.GestaoInstitucional]);
      await http().get(PERIODO).set(auth(gin.token)).expect(200);

      for (const papel of [Papel.Tecnico, Papel.Comunicacao]) {
        const outro = await logado(app, [papel]);
        esperarErro(await http().get(PERIODO).set(auth(outro.token)), {
          status: 403,
        });
      }
    });

    it('period missing or reversed: 422', async () => {
      esperarErro(await http().get('/linha-do-tempo').set(auth()), {
        status: 422,
      });
      esperarErro(
        await http()
          .get(
            '/linha-do-tempo?inicio=2026-11-03T00:00:00Z&fim=2026-11-02T00:00:00Z',
          )
          .set(auth()),
        { status: 422 },
      );
    });
  });
});
