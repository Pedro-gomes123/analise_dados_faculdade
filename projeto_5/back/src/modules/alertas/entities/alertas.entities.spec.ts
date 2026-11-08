import { CriaTabelasAlertasAcoes1792900000001 } from '@/infrastructure/database/migrations/1792900000001-CriaTabelasAlertasAcoes';
import {
  columnsCreatedIn,
  loadEntityMetadata,
} from '@/infrastructure/database/testing/entity-metadata';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { ControleAvaliacaoAlerta } from '@/modules/alertas/entities/controle-avaliacao-alerta.entity';
import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';
import type { QueryRunner } from 'typeorm';

const ENTITIES = [
  Usuario,
  UsuarioPapel,
  ParametroAlerta,
  ParametroAlertaHistorico,
  Alerta,
  Acao,
  ControleAvaliacaoAlerta,
];

async function migrationStatements(
  direction: 'up' | 'down',
): Promise<string[]> {
  const statements: string[] = [];
  const runner = {
    query: (sql: string) => {
      statements.push(sql);
      return Promise.resolve();
    },
  } as unknown as QueryRunner;
  await new CriaTabelasAlertasAcoes1792900000001()[direction](runner);
  return statements;
}

describe('alert and action entities (erd.md)', () => {
  const cases = [
    { entity: ParametroAlerta, table: 'parametro_alerta' },
    { entity: ParametroAlertaHistorico, table: 'parametro_alerta_historico' },
    { entity: Alerta, table: 'alerta' },
    { entity: Acao, table: 'acao' },
    { entity: ControleAvaliacaoAlerta, table: 'controle_avaliacao_alerta' },
  ];

  it.each(cases)(
    '$table lives in the app schema',
    async ({ entity, table }) => {
      const metadataOf = await loadEntityMetadata(ENTITIES);

      expect(metadataOf(entity).tablePath).toBe(`app.${table}`);
    },
  );

  it.each(cases)(
    '$table entity columns match the migration',
    async ({ entity, table }) => {
      const metadataOf = await loadEntityMetadata(ENTITIES);
      const sql = (await migrationStatements('up')).join('\n');

      const entityColumns = metadataOf(entity)
        .columns.map((column) => column.databaseName)
        .sort();

      expect(entityColumns).toEqual(columnsCreatedIn(sql, table).sort());
    },
  );

  it.each([
    { entity: ParametroAlertaHistorico, column: 'valor_anterior' },
    { entity: Alerta, column: 'dthr_encerramento' },
    { entity: Acao, column: 'id_alerta' },
    { entity: ControleAvaliacaoAlerta, column: 'ultima_lida_em' },
  ])('$column is nullable', async ({ entity, column }) => {
    const metadataOf = await loadEntityMetadata(ENTITIES);

    expect(
      metadataOf(entity).findColumnWithDatabaseName(column)?.isNullable,
    ).toBe(true);
  });

  it('acao has no update timestamp (RN-004 #5, DEC-014)', async () => {
    const metadataOf = await loadEntityMetadata(ENTITIES);

    expect(
      metadataOf(Acao).findColumnWithDatabaseName('dthr_atualizacao'),
    ).toBeUndefined();
  });
});

describe('CriaTabelasAlertasAcoes migration', () => {
  it('enforces one alert per reading (RN-003)', async () => {
    const sql = (await migrationStatements('up')).join('\n');

    expect(sql).toContain(
      'CONSTRAINT [uq_alerta_parametro_leitura] UNIQUE ([id_parametro_alerta], [fonte], [estacao], [lida_em])',
    );
  });

  it('creates the single job control row (DEC-015)', async () => {
    const statements = await migrationStatements('up');

    expect(statements.at(-1)).toBe(
      'INSERT INTO [app].[controle_avaliacao_alerta] ([ultima_lida_em]) VALUES (NULL)',
    );
  });

  it('drops the tables in reverse dependency order', async () => {
    expect(await migrationStatements('down')).toEqual([
      'DROP TABLE [app].[controle_avaliacao_alerta]',
      'DROP TABLE [app].[acao]',
      'DROP TABLE [app].[alerta]',
      'DROP TABLE [app].[parametro_alerta_historico]',
      'DROP TABLE [app].[parametro_alerta]',
    ]);
  });
});
