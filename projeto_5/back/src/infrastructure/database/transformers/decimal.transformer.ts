import { ValueTransformer } from 'typeorm';

// The mssql driver may return decimal as string; the API works with numbers.
export const decimalTransformer: ValueTransformer = {
  to: (value: unknown) => value,
  from: (value: unknown) => (typeof value === 'string' ? Number(value) : value),
};
