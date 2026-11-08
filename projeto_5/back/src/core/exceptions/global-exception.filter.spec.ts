import {
  ArgumentsHost,
  HttpStatus,
  InternalServerErrorException,
  Logger,
  NotFoundException,
  UnprocessableEntityException,
} from '@nestjs/common';
import { BusinessRuleException } from '@/core/exceptions/business-rule.exception';
import {
  ErrorResponse,
  GlobalExceptionFilter,
} from '@/core/exceptions/global-exception.filter';

function run(exception: unknown, isProduction = false) {
  const json = jest.fn();
  const status = jest.fn().mockReturnValue({ json });
  const host = {
    switchToHttp: () => ({
      getRequest: () => ({ url: '/recurso/10' }),
      getResponse: () => ({ status }),
    }),
  } as unknown as ArgumentsHost;

  new GlobalExceptionFilter(isProduction).catch(exception, host);

  const [[body]] = json.mock.calls as [[ErrorResponse]];
  const [[code]] = status.mock.calls as [[number]];
  return { code, body };
}

describe('GlobalExceptionFilter', () => {
  let logError: jest.SpyInstance;

  beforeEach(() => {
    logError = jest
      .spyOn(Logger.prototype, 'error')
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('formats an HttpException', () => {
    const { code, body } = run(new NotFoundException('Alerta não encontrado'));

    expect(code).toBe(404);
    expect(body).toMatchObject({
      status_code: 404,
      error: 'Not Found',
      message: 'Alerta não encontrado',
      path: '/recurso/10',
    });
    expect(body.business_rule_code).toBeUndefined();
    expect(Number.isNaN(Date.parse(body.timestamp))).toBe(false);
  });

  it('keeps the field errors of a validation failure', () => {
    const errors = [
      { property: 'email', constraints: { isEmail: 'E-mail inválido' } },
    ];
    const { code, body } = run(
      new UnprocessableEntityException({ message: 'Dados inválidos', errors }),
    );

    expect(code).toBe(422);
    expect(body.message).toBe('Dados inválidos');
    expect(body.errors).toEqual(errors);
  });

  it('adds the business rule code', () => {
    const { code, body } = run(
      new BusinessRuleException({
        code: 'EMAIL_JA_CADASTRADO',
        message: 'Já existe um usuário com este e-mail',
        status: HttpStatus.CONFLICT,
      }),
    );

    expect(code).toBe(409);
    expect(body.business_rule_code).toBe('EMAIL_JA_CADASTRADO');
    expect(body.message).toBe('Já existe um usuário com este e-mail');
  });

  it('turns an unknown error into a 500 without leaking it, and logs it', () => {
    const { code, body } = run(new TypeError('cannot read x of undefined'));

    expect(code).toBe(500);
    expect(body.message).toBe('Erro interno do servidor');
    expect(logError).toHaveBeenCalled();
  });

  it('hides the message of a 5xx HttpException in production', () => {
    const { body } = run(
      new InternalServerErrorException('pool exhausted'),
      true,
    );

    expect(body.message).toBe('Erro interno do servidor');
  });

  it('shows the message of a 5xx HttpException outside production', () => {
    const { body } = run(
      new InternalServerErrorException('pool exhausted'),
      false,
    );

    expect(body.message).toBe('pool exhausted');
  });
});
