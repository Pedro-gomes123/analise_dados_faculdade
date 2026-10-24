import 'reflect-metadata';
import { NodeEnv, validateEnv } from '@/core/config/env.validation';

const requiredEnv = {
  DB_HOST: 'localhost',
  DB_USER: 'sa',
  DB_PASSWORD: 'secret',
  DB_NAME: 'vigia',
};

describe('validateEnv', () => {
  it('applies defaults when optional variables are missing', () => {
    const env = validateEnv(requiredEnv);

    expect(env.NODE_ENV).toBe(NodeEnv.Development);
    expect(env.PORT).toBe(3000);
    expect(env.DB_PORT).toBe(1433);
    expect(env.DB_ENCRYPT).toBe(true);
    expect(env.DB_TRUST_SERVER_CERTIFICATE).toBe(false);
  });

  it('converts numbers and booleans from strings', () => {
    const env = validateEnv({
      ...requiredEnv,
      PORT: '8080',
      DB_ENCRYPT: 'false',
      DB_TRUST_SERVER_CERTIFICATE: 'true',
    });

    expect(env.PORT).toBe(8080);
    expect(env.DB_ENCRYPT).toBe(false);
    expect(env.DB_TRUST_SERVER_CERTIFICATE).toBe(true);
  });

  it('rejects an invalid PORT', () => {
    expect(() => validateEnv({ ...requiredEnv, PORT: 'abc' })).toThrow(/PORT/);
  });

  it('rejects an unknown NODE_ENV', () => {
    expect(() => validateEnv({ ...requiredEnv, NODE_ENV: 'staging' })).toThrow(
      /NODE_ENV/,
    );
  });

  it('requires the database connection variables', () => {
    expect(() => validateEnv({})).toThrow(/DB_HOST/);
  });
});
