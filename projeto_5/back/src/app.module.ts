import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { APP_FILTER, APP_PIPE } from '@nestjs/core';
import { AppController } from '@/app.controller';
import { AppService } from '@/app.service';
import {
  EnvironmentVariables,
  NodeEnv,
  validateEnv,
} from '@/core/config/env.validation';
import { GlobalExceptionFilter } from '@/core/exceptions/global-exception.filter';
import { createValidationPipe } from '@/core/pipes/validation.pipe';
import { DatabaseModule } from '@/infrastructure/database/database.module';
import { AcessoModule } from '@/modules/acesso/acesso.module';
import { AlertasModule } from '@/modules/alertas/alertas.module';
import { HealthModule } from '@/modules/health/health.module';
import { RastreioOperacionalModule } from '@/modules/rastreio-operacional/rastreio-operacional.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, validate: validateEnv }),
    DatabaseModule,
    HealthModule,
    AcessoModule,
    AlertasModule,
    RastreioOperacionalModule,
  ],
  controllers: [AppController],
  providers: [
    AppService,
    // Registered as providers (not in main.ts) so e2e tests get the same behavior.
    { provide: APP_PIPE, useFactory: createValidationPipe },
    {
      provide: APP_FILTER,
      inject: [ConfigService],
      useFactory: (config: ConfigService<EnvironmentVariables, true>) =>
        new GlobalExceptionFilter(
          config.get('NODE_ENV', { infer: true }) === NodeEnv.Production,
        ),
    },
  ],
})
export class AppModule {}
