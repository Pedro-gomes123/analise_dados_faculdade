import request from 'supertest';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { criarAlerta, registrarAcaoEm } from './helpers/e2e-alertas';
import { type AppE2e, criarAppE2e, limparBanco } from './helpers/e2e-app';
import { camposInvalidos, esperarErro } from './helpers/e2e-erro';
import { logado } from './helpers/e2e-usuarios';

const HORA_MS = 60 * 60_000;

// PER-012, RN-009, PR-022, DEC-019.
describe('Boletins (e2e)', () => {
  let app: AppE2e;
  let comunicacao: Awaited<ReturnType<typeof logado>>;

  beforeAll(async () => {
    app = await criarAppE2e();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await limparBanco(app);
    comunicacao = await logado(app, [Papel.Comunicacao]);
  });

  const post = (url: string, corpo: object, token = comunicacao.token) =>
    request(app.getHttpServer())
      .post(url)
      .set('Authorization', `Bearer ${token}`)
      .send(corpo);

  const previa = (corpo: object, token?: string) =>
    post('/boletins/pre-visualizacao', corpo, token);

  const pdf = (corpo: object, token?: string) =>
    post('/boletins/pdf', corpo, token).responseType('blob');

  it('previews the chosen sections in the RN-009 order, with the actions of the last 24 h (PR-022)', async () => {
    const agora = Date.now();
    const alerta = await criarAlerta(app, {
      disparadoEm: new Date(agora - 2 * HORA_MS),
    });
    await registrarAcaoEm(app, {
      descricao: 'Equipe enviada <script>alert(1)</script>',
      idUsuario: comunicacao.usuario.id,
      idAlerta: alerta.id,
      registradaEm: new Date(agora - HORA_MS),
    });
    await registrarAcaoEm(app, {
      descricao: 'Ação antiga',
      idUsuario: comunicacao.usuario.id,
      registradaEm: new Date(agora - 25 * HORA_MS),
    });

    const res = await previa({
      secoes: ['acoes_abrigos', 'rios', 'cabecalho', 'rios'],
    }).expect(200);

    expect(res.headers['content-type']).toBe('text/html; charset=utf-8');
    const html = res.text;
    const posicoes = ['cabecalho', 'rios', 'acoes_abrigos'].map((secao) =>
      html.indexOf(`data-secao="${secao}"`),
    );
    expect(posicoes.every((p) => p >= 0)).toBe(true);
    expect([...posicoes].sort((a, b) => a - b)).toEqual(posicoes);
    expect(html.match(/data-secao="rios"/g)).toHaveLength(1);
    expect(html).not.toContain('data-secao="meteorologia"');

    expect(html).toContain(
      `Equipe enviada &lt;script&gt;alert(1)&lt;/script&gt; (${comunicacao.usuario.nome}, alerta nº ${alerta.id})`,
    );
    expect(html).not.toContain('<script>');
    expect(html).not.toContain('Ação antiga');
  });

  it('generates the PDF named after the date (RN-009 #4, DEC-019)', async () => {
    await registrarAcaoEm(app, {
      descricao: 'Equipe enviada',
      idUsuario: comunicacao.usuario.id,
      registradaEm: new Date(Date.now() - HORA_MS),
    });

    const res = await pdf({ secoes: ['cabecalho', 'acoes_abrigos'] }).expect(
      200,
    );

    expect(res.headers['content-type']).toBe('application/pdf');
    expect(res.headers['content-disposition']).toMatch(
      /^attachment; filename="boletim-\d{4}-\d{2}-\d{2}\.pdf"$/,
    );
    const arquivo = res.body as Buffer;
    expect(arquivo.subarray(0, 5).toString()).toBe('%PDF-');
    expect(Number(res.headers['content-length'])).toBe(arquivo.length);
  });

  it.each([Papel.Tecnico, Papel.Administrador])(
    '%s also generates it (PER-012, PR-023)',
    async (papel) => {
      const outro = await logado(app, [papel]);

      await previa({ secoes: ['cabecalho'] }, outro.token).expect(200);
      await pdf({ secoes: ['cabecalho'] }, outro.token).expect(200);
    },
  );

  it.each([Papel.Gestor, Papel.GestaoInstitucional])(
    '%s cannot generate it: 403 (PER-012)',
    async (papel) => {
      const outro = await logado(app, [papel]);

      esperarErro(await previa({ secoes: ['cabecalho'] }, outro.token), {
        status: 403,
      });
      esperarErro(
        await post('/boletins/pdf', { secoes: ['cabecalho'] }, outro.token),
        {
          status: 403,
        },
      );
    },
  );

  it.each([
    ['no section', { secoes: [] }],
    ['an unknown section', { secoes: ['abrigos'] }],
  ])('%s: 422 in JSON on both endpoints (RN-009 #2, #3)', async (_, corpo) => {
    expect(camposInvalidos(await previa(corpo))).toEqual(['secoes']);
    expect(camposInvalidos(await post('/boletins/pdf', corpo))).toEqual([
      'secoes',
    ]);
  });
});
