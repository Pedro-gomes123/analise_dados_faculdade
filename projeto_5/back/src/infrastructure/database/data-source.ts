// Entry point for the TypeORM CLI (npm run migration:*). The app itself uses
// DatabaseModule; both share buildDatabaseOptions.
import 'dotenv/config';
import 'reflect-metadata';
import { join } from 'node:path';
import { DataSource } from 'typeorm';
import { validateEnv } from '@/core/config/env.validation';
import { buildDatabaseOptions } from '@/infrastructure/database/database.options';

const env = validateEnv(process.env);

export default new DataSource({
  ...buildDatabaseOptions(env),
  entities: [join(__dirname, '..', '..', '**', '*.entity.{ts,js}')],
});
