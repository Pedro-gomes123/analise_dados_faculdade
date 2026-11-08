import { HttpStatus } from '@nestjs/common';
import { defineBusinessRules } from '@/core/exceptions/business-rule.exception';

// Business rule catalog of MOD-001 (regras-negocio.md).
export const AcessoRules = defineBusinessRules({
  // RN-010 #2: unique even among inactive users.
  EMAIL_JA_CADASTRADO: {
    message: 'Já existe um usuário com este e-mail',
    status: HttpStatus.CONFLICT,
  },
});
