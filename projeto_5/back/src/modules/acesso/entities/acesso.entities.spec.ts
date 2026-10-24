import { CriaTabelasAcesso1792900000000 } from '@/infrastructure/database/migrations/1792900000000-CriaTabelasAcesso';
import {
  columnsCreatedIn,
  loadEntityMetadata,
} from '@/infrastructure/database/testing/entity-metadata';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import type { QueryRunner } from 'typeorm';

async function migrationSql(): Promise<string> {
  const statements: string[] = [];
  const runner = {
    query: (sql: string) => {
      statements.push(sql);
      return Promise.resolve();
    },
  } as unknown as QueryRunner;
  await new CriaTabelasAcesso1792900000000().up(runner);
  return statements.join('\n');
}

describe('acesso entities (erd.md)', () => {
  const cases = [
    { entity: Usuario, table: 'usuario' },
    { entity: UsuarioPapel, table: 'usuario_papel' },
    { entity: RegistroAcesso, table: 'registro_acesso' },
  ];

  it.each(cases)(
    '$table lives in the app schema',
    async ({ entity, table }) => {
      const metadataOf = await loadEntityMetadata([
        Usuario,
        UsuarioPapel,
        RegistroAcesso,
      ]);

      expect(metadataOf(entity).tablePath).toBe(`app.${table}`);
    },
  );

  it.each(cases)(
    '$table entity columns match the migration',
    async ({ entity, table }) => {
      const metadataOf = await loadEntityMetadata([
        Usuario,
        UsuarioPapel,
        RegistroAcesso,
      ]);
      const sql = await migrationSql();

      const entityColumns = metadataOf(entity)
        .columns.map((column) => column.databaseName)
        .sort();

      expect(entityColumns).toEqual(columnsCreatedIn(sql, table).sort());
    },
  );

  it('keeps the password hash out of default selects', async () => {
    const metadataOf = await loadEntityMetadata([
      Usuario,
      UsuarioPapel,
      RegistroAcesso,
    ]);

    const senha = metadataOf(Usuario).findColumnWithDatabaseName('senha_hash');
    expect(senha?.isSelect).toBe(false);
  });

  it('allows registro_acesso without a known user', async () => {
    const metadataOf = await loadEntityMetadata([
      Usuario,
      UsuarioPapel,
      RegistroAcesso,
    ]);

    const idUsuario =
      metadataOf(RegistroAcesso).findColumnWithDatabaseName('id_usuario');
    expect(idUsuario?.isNullable).toBe(true);
  });
});

describe('CriaTabelasAcesso migration', () => {
  it('drops the tables in reverse dependency order', async () => {
    const statements: string[] = [];
    const runner = {
      query: (sql: string) => {
        statements.push(sql);
        return Promise.resolve();
      },
    } as unknown as QueryRunner;

    await new CriaTabelasAcesso1792900000000().down(runner);

    expect(statements).toEqual([
      'DROP TABLE [app].[registro_acesso]',
      'DROP TABLE [app].[usuario_papel]',
      'DROP TABLE [app].[usuario]',
    ]);
  });
});
