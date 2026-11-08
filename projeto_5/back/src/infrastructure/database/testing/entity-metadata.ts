import {
  DataSource,
  EntityMetadata,
  EntityTarget,
  ObjectLiteral,
} from 'typeorm';
import { buildDatabaseOptions } from '@/infrastructure/database/database.options';

// Builds TypeORM metadata without opening a connection, so unit tests can check
// that entities mirror the migrations (erd.md).
class MetadataOnlyDataSource extends DataSource {
  build() {
    return this.buildMetadatas();
  }
}

export async function loadEntityMetadata(
  entities: EntityTarget<ObjectLiteral>[],
): Promise<(entity: EntityTarget<ObjectLiteral>) => EntityMetadata> {
  const dataSource = new MetadataOnlyDataSource({
    ...buildDatabaseOptions({
      DB_HOST: 'localhost',
      DB_PORT: 1433,
      DB_USER: 'unused',
      DB_PASSWORD: 'unused',
      DB_NAME: 'unused',
      DB_ENCRYPT: false,
      DB_TRUST_SERVER_CERTIFICATE: true,
    }),
    entities: entities as DataSource['options']['entities'],
  });
  await dataSource.build();
  return (entity) => dataSource.getMetadata(entity);
}

// Column names declared in "CREATE TABLE [schema].[table] (...)" of a migration's SQL.
export function columnsCreatedIn(sql: string, table: string): string[] {
  const block = new RegExp(
    String.raw`CREATE TABLE \[app\]\.\[${table}\] \(([\s\S]*?)\n\s*\)\s*$`,
    'm',
  ).exec(sql);
  if (!block) throw new Error(`CREATE TABLE app.${table} not found`);
  return [...block[1].matchAll(/^\s*\[(\w+)\]\s+\w/gm)].map((m) => m[1]);
}
