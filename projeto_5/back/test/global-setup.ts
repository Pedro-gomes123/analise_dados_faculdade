import { execSync } from 'node:child_process';
import { DataSource } from 'typeorm';
import { buildDatabaseOptions } from '../src/infrastructure/database/database.options';
import { aplicarAmbienteE2e } from './e2e-ambiente';

// Relative imports only: globalSetup does not go through moduleNameMapper.
function conexao(database: string): DataSource {
  const env = process.env;
  return new DataSource({
    ...buildDatabaseOptions({
      DB_HOST: env.DB_HOST ?? 'localhost',
      DB_PORT: Number(env.DB_PORT ?? 1433),
      DB_USER: env.DB_USER ?? 'sa',
      DB_PASSWORD: env.DB_PASSWORD ?? '',
      DB_NAME: database,
      DB_ENCRYPT: env.DB_ENCRYPT !== 'false',
      DB_TRUST_SERVER_CERTIFICATE: env.DB_TRUST_SERVER_CERTIFICATE === 'true',
    }),
    migrations: [],
  });
}

async function executar(database: string, sql: string) {
  const fonte = await conexao(database).initialize();
  try {
    await fonte.query(sql);
  } finally {
    await fonte.destroy();
  }
}

// Requires the SQL Server of compose.yml (docker compose up -d --wait).
// Creates the e2e database and the app schema (what db-init does for the
// development database) and applies the migrations with the same CLI as
// production (DEC-008), so the e2e also prove the migrations.
export default async function globalSetup() {
  const banco = aplicarAmbienteE2e();

  await executar(
    'master',
    `IF DB_ID('${banco}') IS NULL CREATE DATABASE [${banco}]`,
  );
  await executar(
    banco,
    `IF SCHEMA_ID('app') IS NULL EXEC('CREATE SCHEMA app')`,
  );

  try {
    execSync('npm run migration:run', { env: process.env, stdio: 'pipe' });
  } catch (error) {
    const { stdout, stderr } = error as { stdout?: Buffer; stderr?: Buffer };
    console.error(stdout?.toString(), stderr?.toString());
    throw error;
  }
}
