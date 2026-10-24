import type { Response } from 'supertest';
import type { ErrorResponse } from '@/core/exceptions/global-exception.filter';

interface ErroEsperado {
  status: number;
  message?: string;
  businessRuleCode?: string;
}

// Every error follows the same contract (DEC-010, DEC-011).
export function esperarErro(res: Response, esperado: ErroEsperado) {
  const corpo = res.body as ErrorResponse;

  expect(res.status).toBe(esperado.status);
  expect(res.headers['content-type']).toMatch(/application\/json/);
  expect(corpo.status_code).toBe(esperado.status);
  expect(typeof corpo.error).toBe('string');
  expect(typeof corpo.timestamp).toBe('string');
  expect(typeof corpo.path).toBe('string');
  if (esperado.message !== undefined) {
    expect(corpo.message).toBe(esperado.message);
  }
  if (esperado.businessRuleCode !== undefined) {
    expect(corpo.business_rule_code).toBe(esperado.businessRuleCode);
  }
}

// 422 with the detail of the invalid fields (DEC-010).
export function camposInvalidos(res: Response): string[] {
  esperarErro(res, { status: 422, message: 'Dados inválidos' });
  const { errors } = res.body as { errors: { property: string }[] };
  return errors.map((erro) => erro.property);
}
