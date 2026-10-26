import { DataSource } from 'typeorm';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { StatusAlerta } from '@/modules/alertas/enums/status-alerta.enum';
import type { AppE2e } from './e2e-app';

interface DadosAlerta {
  disparadoEm: Date;
  territorio?: string;
  nivel?: string;
  status?: StatusAlerta;
}

// Alerts come from the job (TASK-035, blocked by the gold contract), so the
// e2e insert them straight in the database, each with its own parameter.
export async function criarAlerta(
  app: AppE2e,
  dados: DadosAlerta,
): Promise<Alerta> {
  const fonte = app.get(DataSource);
  const territorio = dados.territorio ?? 'RPA-1';
  const nivel = dados.nivel ?? 'ALTO';
  const parametro = await fonte.getRepository(ParametroAlerta).save({
    variavel: 'chuva_1h',
    territorio,
    limiar: 50,
    nivel,
  });
  return fonte.getRepository(Alerta).save({
    idParametroAlerta: parametro.id,
    variavel: parametro.variavel,
    territorio,
    limiar: parametro.limiar,
    nivel,
    fonte: 'APAC',
    estacao: 'E2E',
    valorLido: 62.5,
    lidaEm: new Date(dados.disparadoEm.getTime() - 5 * 60_000),
    status: dados.status ?? StatusAlerta.Ativo,
    dthrDisparo: dados.disparadoEm,
  });
}

interface DadosAcao {
  descricao: string;
  idUsuario: number;
  idAlerta?: number;
  registradaEm: Date;
}

// The API always stamps the server time (RN-004); a fixed time is only
// possible straight in the database.
export async function registrarAcaoEm(app: AppE2e, dados: DadosAcao) {
  await app
    .get(DataSource)
    .query(
      'INSERT INTO [app].[acao] ([descricao], [id_alerta], [id_usuario], [dthr_criacao]) VALUES (@0, @1, @2, @3)',
      [
        dados.descricao,
        dados.idAlerta ?? null,
        dados.idUsuario,
        dados.registradaEm,
      ],
    );
}
