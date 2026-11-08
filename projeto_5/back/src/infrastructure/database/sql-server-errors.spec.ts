import { isUniqueViolation } from '@/infrastructure/database/sql-server-errors';

describe('isUniqueViolation', () => {
  it('detects unique constraint and unique index violations from TypeORM', () => {
    expect(isUniqueViolation({ driverError: { number: 2627 } })).toBe(true);
    expect(isUniqueViolation({ driverError: { number: 2601 } })).toBe(true);
  });

  it('detects the number on the raw driver error', () => {
    expect(isUniqueViolation({ number: 2627 })).toBe(true);
  });

  it('ignores other errors', () => {
    expect(isUniqueViolation({ driverError: { number: 547 } })).toBe(false);
    expect(isUniqueViolation(new Error('x'))).toBe(false);
    expect(isUniqueViolation(null)).toBe(false);
  });
});
