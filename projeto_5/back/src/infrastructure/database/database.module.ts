import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { EnvironmentVariables } from '@/core/config/env.validation';

@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService<EnvironmentVariables, true>) => ({
        type: 'mssql',
        host: config.get('DB_HOST', { infer: true }),
        port: config.get('DB_PORT', { infer: true }),
        username: config.get('DB_USER', { infer: true }),
        password: config.get('DB_PASSWORD', { infer: true }),
        database: config.get('DB_NAME', { infer: true }),
        options: {
          encrypt: config.get('DB_ENCRYPT', { infer: true }),
          trustServerCertificate: config.get('DB_TRUST_SERVER_CERTIFICATE', {
            infer: true,
          }),
        },
        autoLoadEntities: true,
        // Schemas bronze/silver/gold belong to the data pipeline (DEC-006, DEC-008).
        synchronize: false,
        migrationsRun: false,
      }),
    }),
  ],
})
export class DatabaseModule {}
