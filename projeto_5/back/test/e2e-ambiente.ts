import 'dotenv/config';

const SUFIXO = '_e2e';

// The e2e never touch the development database: same server (compose.yml),
// own database. Real environment variables win over .env (dotenv does not
// override them), and DB_NAME gets the suffix only once.
export function aplicarAmbienteE2e(): string {
  const base = process.env.DB_NAME ?? 'vigia';
  const banco = base.endsWith(SUFIXO) ? base : `${base}${SUFIXO}`;
  // Goes into CREATE DATABASE, which takes no parameters.
  if (!/^\w+$/.test(banco)) {
    throw new Error(`DB_NAME inválido para os e2e: ${banco}`);
  }
  process.env.DB_NAME = banco;
  process.env.NODE_ENV = 'test';
  return banco;
}
