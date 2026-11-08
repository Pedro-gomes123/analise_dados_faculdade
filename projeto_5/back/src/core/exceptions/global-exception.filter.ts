import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { STATUS_CODES } from 'node:http';
import type { Request, Response } from 'express';
import { BusinessRuleException } from '@/core/exceptions/business-rule.exception';

export interface ErrorResponse {
  status_code: number;
  error: string;
  message: string | string[];
  business_rule_code?: string;
  errors?: unknown[];
  timestamp: string;
  path: string;
}

const INTERNAL_ERROR_MESSAGE = 'Erro interno do servidor';

// Single error contract for the whole API (DEC-010, DEC-011).
@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(GlobalExceptionFilter.name);

  constructor(private readonly isProduction: boolean) {}

  catch(exception: unknown, host: ArgumentsHost) {
    const http = host.switchToHttp();
    const request = http.getRequest<Request>();
    const response = http.getResponse<Response>();

    const status =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    const body: ErrorResponse = {
      status_code: status,
      error: STATUS_CODES[status] ?? 'Error',
      message: INTERNAL_ERROR_MESSAGE,
      timestamp: new Date().toISOString(),
      path: request.url,
    };

    if (status >= 500) {
      this.logger.error(
        exception instanceof Error ? exception.stack : String(exception),
      );
    }

    if (
      exception instanceof HttpException &&
      !(status >= 500 && this.isProduction)
    ) {
      const payload = exception.getResponse();
      if (typeof payload === 'string') {
        body.message = payload;
      } else {
        const { message, errors } = payload as {
          message?: string | string[];
          errors?: unknown[];
        };
        body.message = message ?? exception.message;
        if (errors) body.errors = errors;
      }
    }

    if (exception instanceof BusinessRuleException) {
      body.business_rule_code = exception.businessRuleCode;
    }

    response.status(status).json(body);
  }
}
