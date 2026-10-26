// SQL Server error numbers the app translates into HTTP responses (DEC-010).
export enum SqlServerError {
  UniqueConstraintViolation = 2627,
  UniqueIndexViolation = 2601,
  ForeignKeyViolation = 547,
}

function errorNumber(error: unknown): number | undefined {
  if (typeof error !== 'object' || error === null) return undefined;
  const { number, driverError } = error as {
    number?: unknown;
    driverError?: { number?: unknown };
  };
  const value = driverError?.number ?? number;
  return typeof value === 'number' ? value : undefined;
}

export function isUniqueViolation(error: unknown): boolean {
  const code = errorNumber(error);
  return (
    code === SqlServerError.UniqueConstraintViolation ||
    code === SqlServerError.UniqueIndexViolation
  );
}
