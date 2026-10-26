import request from 'supertest';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { criarAlerta, registrarAcaoEm } from './helpers/e2e-alertas';
import { type AppE2e, criarAppE2e, limparBanco } from './helpers/e2e-app';
import { esperarErro } from './helpers/e2e-erro';
import { logado } from './helpers/e2e-usuarios';

const URL =
  '/indicadores/tempo-acionamento?inicio=2026-11-02T00:00:00Z&fim=2026-11-02T23:59:59Z';

const em = (hora: string) => new Date(`2026-11-02T${hora}:00Z`);

// PER-009, RN-006, PR-021. The grouped MIN() query only runs on a real database.
describe('Tempo de acionamento (e2e)', () => {
  let app: AppE2e;
  let gin: Awaited<ReturnType<typeof logado>>;

  beforeAll(async () => {
    app = await criarAppE2e();
  });

  afterAll(async () => {
    await app.close();
  });

  beforeEach(async () => {
    await limparBanco(app);
    gin = await logado(app, [Papel.GestaoInstitucional]);
  });

  const consultar = (token = gin.token) =>
    request(app.getHttpServer())
      .get(URL)
      .set('Authorization', `Bearer ${token}`);

  it('uses the first linked action, averages only alerts with action and lists the others apart', async () => {
    const autor = gin.usuario.id;
    const comDuas = await criarAlerta(app, {
      disparadoEm: em('10:00'),
      territorio: 'RPA-1',
    });
    const comUma = await criarAlerta(app, {
      disparadoEm: em('11:00'),
      territorio: 'RPA-2',
    });
    const semAcao = await criarAlerta(app, {
      disparadoEm: em('12:00'),
      territorio: 'RPA-3',
    });
    const foraDoPeriodo = await criarAlerta(app, {
      disparadoEm: new Date('2026-11-03T10:00:00Z'),
    });

    // RN-006 #1: the first one counts, whatever the insertion order.
    for (const [idAlerta, hora] of [
      [comDuas.id, '10:30'],
      [comDuas.id, '10:10'],
      [comUma.id, '12:00'],
    ] as const) {
      await registrarAcaoEm(app, {
        descricao: 'Ação',
        idUsuario: autor,
        idAlerta,
        registradaEm: em(hora),
      });
    }
    // Not linked: never counts.
    await registrarAcaoEm(app, {
      descricao: 'Avulsa',
      idUsuario: autor,
      registradaEm: em('10:01'),
    });
    await registrarAcaoEm(app, {
      descricao: 'Fora',
      idUsuario: autor,
      idAlerta: foraDoPeriodo.id,
      registradaEm: new Date('2026-11-03T10:05:00Z'),
    });

    const res = await consultar().expect(200);

    expect(res.body).toEqual({
      inicio: '2026-11-02T00:00:00.000Z',
      fim: '2026-11-02T23:59:59.000Z',
      // (600 s + 3600 s) / 2: the alert without action stays out (PR-021).
      media_segundos: 2100,
      alertas_com_acao: 2,
      alertas_sem_acao: 1,
      alertas: [
        {
          id: comDuas.id,
          variavel: 'chuva_1h',
          territorio: 'RPA-1',
          nivel: 'ALTO',
          disparado_em: '2026-11-02T10:00:00.000Z',
          primeira_acao_em: '2026-11-02T10:10:00.000Z',
          tempo_segundos: 600,
        },
        {
          id: comUma.id,
          variavel: 'chuva_1h',
          territorio: 'RPA-2',
          nivel: 'ALTO',
          disparado_em: '2026-11-02T11:00:00.000Z',
          primeira_acao_em: '2026-11-02T12:00:00.000Z',
          tempo_segundos: 3600,
        },
        {
          id: semAcao.id,
          variavel: 'chuva_1h',
          territorio: 'RPA-3',
          nivel: 'ALTO',
          disparado_em: '2026-11-02T12:00:00.000Z',
          primeira_acao_em: null,
          tempo_segundos: null,
        },
      ],
    });
  });

  it('no alert in the period: no average', async () => {
    const res = await consultar().expect(200);

    expect(res.body).toMatchObject({
      media_segundos: null,
      alertas_com_acao: 0,
      alertas_sem_acao: 0,
      alertas: [],
    });
  });

  it.each([Papel.Gestor, Papel.Tecnico, Papel.Comunicacao])(
    '%s cannot read it: 403 (PER-009)',
    async (papel) => {
      const outro = await logado(app, [papel]);
      esperarErro(await consultar(outro.token), { status: 403 });
    },
  );
});
