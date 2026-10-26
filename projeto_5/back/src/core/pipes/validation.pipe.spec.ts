import 'reflect-metadata';
import { UnprocessableEntityException } from '@nestjs/common';
import { Type } from 'class-transformer';
import { IsEmail, IsInt, IsString, ValidateNested } from 'class-validator';
import {
  createValidationPipe,
  FieldError,
  VALIDATION_MESSAGE,
} from '@/core/pipes/validation.pipe';

class EnderecoDto {
  @IsString()
  cep!: string;
}

class ExemploDto {
  @IsEmail()
  email!: string;

  @IsInt()
  idade!: number;

  @ValidateNested()
  @Type(() => EnderecoDto)
  endereco!: EnderecoDto;
}

async function validate(value: unknown) {
  return createValidationPipe().transform(value, {
    type: 'body',
    metatype: ExemploDto,
  }) as Promise<unknown>;
}

async function errorsOf(value: unknown): Promise<FieldError[]> {
  try {
    await validate(value);
  } catch (error) {
    expect(error).toBeInstanceOf(UnprocessableEntityException);
    const response = (error as UnprocessableEntityException).getResponse() as {
      message: string;
      errors: FieldError[];
    };
    expect(response.message).toBe(VALIDATION_MESSAGE);
    return response.errors;
  }
  throw new Error('expected validation to fail');
}

describe('createValidationPipe', () => {
  it('accepts a valid body and returns the DTO instance', async () => {
    const result = await validate({
      email: 'a@b.com',
      idade: 30,
      endereco: { cep: '50000-000' },
    });

    expect(result).toBeInstanceOf(ExemploDto);
  });

  it('rejects invalid fields with 422 and the property names', async () => {
    const errors = await errorsOf({
      email: 'x',
      idade: 'trinta',
      endereco: { cep: '50000-000' },
    });

    expect(errors.map((e) => e.property).sort()).toEqual(['email', 'idade']);
  });

  it('rejects unknown fields with 422 instead of 400', async () => {
    const errors = await errorsOf({
      email: 'a@b.com',
      idade: 30,
      endereco: { cep: '50000-000' },
      autor: 'hacker',
    });

    expect(errors).toEqual([expect.objectContaining({ property: 'autor' })]);
  });

  it('reports nested errors with a dotted path', async () => {
    const errors = await errorsOf({
      email: 'a@b.com',
      idade: 30,
      endereco: { cep: 123 },
    });

    expect(errors).toEqual([
      expect.objectContaining({ property: 'endereco.cep' }),
    ]);
  });
});
