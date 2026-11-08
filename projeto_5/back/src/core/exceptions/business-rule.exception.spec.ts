import { HttpStatus } from '@nestjs/common';
import {
  BusinessRuleException,
  defineBusinessRules,
} from '@/core/exceptions/business-rule.exception';

describe('BusinessRuleException', () => {
  it('defaults to 412 and keeps the rule code', () => {
    const exception = new BusinessRuleException({
      code: 'REGRA_X',
      message: 'Regra violada',
    });

    expect(exception.getStatus()).toBe(HttpStatus.PRECONDITION_FAILED);
    expect(exception.businessRuleCode).toBe('REGRA_X');
    expect(exception.message).toBe('Regra violada');
  });

  it('uses the status defined by the rule', () => {
    const exception = new BusinessRuleException({
      code: 'DUPLICADO',
      message: 'Já existe',
      status: HttpStatus.CONFLICT,
    });

    expect(exception.getStatus()).toBe(HttpStatus.CONFLICT);
  });
});

describe('defineBusinessRules', () => {
  it('uses each key as the rule code', () => {
    const rules = defineBusinessRules({
      EMAIL_JA_CADASTRADO: {
        message: 'Já existe um usuário com este e-mail',
        status: HttpStatus.CONFLICT,
      },
    });

    expect(rules.EMAIL_JA_CADASTRADO).toEqual({
      code: 'EMAIL_JA_CADASTRADO',
      message: 'Já existe um usuário com este e-mail',
      status: HttpStatus.CONFLICT,
    });
  });
});
