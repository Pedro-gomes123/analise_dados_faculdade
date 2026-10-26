import {
  UnprocessableEntityException,
  ValidationError,
  ValidationPipe,
} from '@nestjs/common';

export interface FieldError {
  property: string;
  constraints: Record<string, string>;
}

export const VALIDATION_MESSAGE = 'Dados inválidos';

// Nested DTO errors become dotted paths: endereco.cep, itens.0.quantidade.
export function flattenValidationErrors(
  errors: ValidationError[],
  parent?: string,
): FieldError[] {
  return errors.flatMap((error) => {
    const property = parent ? `${parent}.${error.property}` : error.property;
    const own: FieldError[] = error.constraints
      ? [{ property, constraints: error.constraints }]
      : [];
    return [...own, ...flattenValidationErrors(error.children ?? [], property)];
  });
}

// One pipe, one status: invalid body, query or param and unknown fields are all 422 (DEC-010).
export function createValidationPipe() {
  return new ValidationPipe({
    transform: true,
    whitelist: true,
    forbidNonWhitelisted: true,
    exceptionFactory: (errors) =>
      new UnprocessableEntityException({
        message: VALIDATION_MESSAGE,
        errors: flattenValidationErrors(errors),
      }),
  });
}
