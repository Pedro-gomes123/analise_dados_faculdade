import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import type { App } from 'supertest/types';
import { DataSource } from 'typeorm';
import { AppModule } from '@/app.module';

export type AppE2e = INestApplication<App>;

// The whole AppModule: pipe, filter and guard are its providers, exactly as in
// main.ts. Swagger is the only thing main.ts adds, and it is not under test.
export async function criarAppE2e(): Promise<AppE2e> {
  const moduleRef = await Test.createTestingModule({
    imports: [AppModule],
  }).compile();
  const app = moduleRef.createNestApplication<AppE2e>();
  await app.init();
  return app;
}

// Foreign key order. controle_avaliacao_alerta keeps the single row the
// migration created.
const TABELAS = [
  'acao',
  'alerta',
  'parametro_alerta_historico',
  'parametro_alerta',
  'registro_acesso',
  'usuario_papel',
  'usuario',
];

export async function limparBanco(app: AppE2e) {
  const fonte = app.get(DataSource);
  for (const tabela of TABELAS) {
    await fonte.query(`DELETE FROM [app].[${tabela}]`);
  }
}
