import {
  APP_SCHEMA,
  buildDatabaseOptions,
  MIGRATIONS_GLOB,
} from '@/infrastructure/database/database.options';

const env = {
  DB_HOST: 'localhost',
  DB_PORT: 1433,
  DB_USER: 'sa',
  DB_PASSWORD: 'secret',
  DB_NAME: 'vigia',
  DB_ENCRYPT: true,
  DB_TRUST_SERVER_CERTIFICATE: false,
};

describe('buildDatabaseOptions', () => {
  it('maps the environment to the SQL Server connection', () => {
    const options = buildDatabaseOptions(env);

    expect(options).toMatchObject({
      type: 'mssql',
      host: 'localhost',
      port: 1433,
      username: 'sa',
      password: 'secret',
      database: 'vigia',
      options: { encrypt: true, trustServerCertificate: false },
    });
  });

  it('keeps entities and the migrations table in the app schema', () => {
    const options = buildDatabaseOptions(env);

    expect(APP_SCHEMA).toBe('app');
    expect(options.schema).toBe('app');
    expect(options.migrationsTableName).toBe('migrations');
  });

  it('never lets TypeORM change the schema on its own', () => {
    const options = buildDatabaseOptions(env);

    expect(options.synchronize).toBe(false);
    expect(options.migrationsRun).toBe(false);
    expect(options.migrations).toEqual([MIGRATIONS_GLOB]);
  });
});
