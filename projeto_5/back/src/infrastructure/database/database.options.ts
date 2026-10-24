import { join } from 'node:path';
import type { SqlServerConnectionOptions } from 'typeorm/driver/sqlserver/SqlServerConnectionOptions';
import type { EnvironmentVariables } from '@/core/config/env.validation';

// Everything the app writes lives in the `app` schema (DEC-016): entities and
// the migrations table default to it. The schema itself is created outside the
// migrations (compose db-init locally; DBA on Azure).
export const APP_SCHEMA = 'app';

export const MIGRATIONS_GLOB = join(__dirname, 'migrations', '*.{ts,js}');

type DatabaseEnv = Pick<
  EnvironmentVariables,
  | 'DB_HOST'
  | 'DB_PORT'
  | 'DB_USER'
  | 'DB_PASSWORD'
  | 'DB_NAME'
  | 'DB_ENCRYPT'
  | 'DB_TRUST_SERVER_CERTIFICATE'
>;

export function buildDatabaseOptions(
  env: DatabaseEnv,
): SqlServerConnectionOptions {
  return {
    type: 'mssql',
    host: env.DB_HOST,
    port: env.DB_PORT,
    username: env.DB_USER,
    password: env.DB_PASSWORD,
    database: env.DB_NAME,
    schema: APP_SCHEMA,
    options: {
      encrypt: env.DB_ENCRYPT,
      trustServerCertificate: env.DB_TRUST_SERVER_CERTIFICATE,
    },
    // Schemas bronze/silver/gold belong to the data pipeline (DEC-006, DEC-008).
    synchronize: false,
    migrationsRun: false,
    migrations: [MIGRATIONS_GLOB],
    migrationsTableName: 'migrations',
  };
}
