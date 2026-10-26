import { decimalTransformer } from '@/infrastructure/database/transformers/decimal.transformer';
import { jsonTransformer } from '@/infrastructure/database/transformers/json.transformer';

describe('jsonTransformer', () => {
  it('stores objects as JSON text and reads them back', () => {
    const valor = { limiar: 50.5, nivel: 'ALTO' };
    const texto: unknown = jsonTransformer.to(valor);

    expect(texto).toBe('{"limiar":50.5,"nivel":"ALTO"}');
    expect(jsonTransformer.from(texto)).toEqual(valor);
  });

  it('keeps null as null', () => {
    expect(jsonTransformer.to(null)).toBeNull();
    expect(jsonTransformer.from(null)).toBeNull();
  });
});

describe('decimalTransformer', () => {
  it('reads decimal strings as numbers', () => {
    expect(decimalTransformer.from('12.345')).toBe(12.345);
  });

  it('keeps numbers as they are', () => {
    expect(decimalTransformer.from(7.5)).toBe(7.5);
    expect(decimalTransformer.to(7.5)).toBe(7.5);
  });
});
