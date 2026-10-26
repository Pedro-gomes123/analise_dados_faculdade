import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import type { App } from 'supertest/types';
import { AppController } from '@/app.controller';
import { AppService } from '@/app.service';
import { setupSwagger } from '@/setup-swagger';

describe('setupSwagger', () => {
  let app: INestApplication<App>;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    app = moduleRef.createNestApplication();
    setupSwagger(app);
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('serves the OpenAPI document with the app routes and bearer auth', async () => {
    const response = await request(app.getHttpServer())
      .get('/docs-json')
      .expect(200);
    const document = response.body as {
      info: { title: string };
      paths: Record<string, unknown>;
      components: { securitySchemes: Record<string, unknown> };
    };

    expect(document.info.title).toBe('O Vigia API');
    expect(Object.keys(document.paths)).toContain('/');
    expect(Object.keys(document.components.securitySchemes)).toContain(
      'bearer',
    );
  });

  it('serves the Swagger UI', async () => {
    await request(app.getHttpServer()).get('/docs').expect(200);
  });
});
