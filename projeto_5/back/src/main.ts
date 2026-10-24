import { NestFactory } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { AppModule } from '@/app.module';
import { EnvironmentVariables, NodeEnv } from '@/core/config/env.validation';
import { setupSwagger } from '@/setup-swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();

  const config = app.get(ConfigService<EnvironmentVariables, true>);
  if (config.get('NODE_ENV', { infer: true }) !== NodeEnv.Production) {
    setupSwagger(app);
  }

  await app.listen(config.get('PORT', { infer: true }));
}
bootstrap().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
