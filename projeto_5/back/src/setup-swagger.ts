import type { INestApplication } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

export const SWAGGER_PATH = 'docs';

// API documentation at /docs (UI) and /docs-json (OpenAPI). Not exposed in production.
export function setupSwagger(app: INestApplication) {
  const config = new DocumentBuilder()
    .setTitle('O Vigia API')
    .setDescription('API da Sala de Situação do Vigidesastres')
    .setVersion('0.1.0')
    .addBearerAuth()
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup(SWAGGER_PATH, app, document, {
    jsonDocumentUrl: `${SWAGGER_PATH}-json`,
  });
  return document;
}
