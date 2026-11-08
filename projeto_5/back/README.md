# O Vigia: API

API da Sala de Situação do Vigidesastres (Secretaria de Saúde do Recife). NestJS 11 + TypeORM, com SQL Server.

O app grava os próprios dados no schema `app`. Os dados climáticos chegam no schema `gold`, preenchido pela pipeline da equipe de dados. A API não escreve nesse schema.

## Requisitos

- **Node 22** (`.nvmrc`). Com Node 20, a conexão com o banco falha com `Promise.withResolvers is not a function`. Use `nvm use` nesta pasta.
- **Docker com Compose**, para o SQL Server local.

## Rodar

Todos os comandos rodam nesta pasta (`projeto_5/back`). Atenção: o `compose.yml` de `projeto_5/` é o da pipeline, não este.

```bash
cp .env.example .env    # preencha senhas, JWT_SECRET e ADMIN_* (instruções no próprio arquivo)
docker compose up -d --build --wait
```

Esse comando sobe o sistema inteiro, em ordem:

| Serviço | O que faz |
|---|---|
| `db` | SQL Server |
| `db-init` | Cria o database e o schema `app` (roda uma vez e termina) |
| `migrate` | Aplica as migrations pendentes e cria o primeiro administrador com os dados `ADMIN_*` (roda uma vez e termina) |
| `api` | API em http://localhost:3000 (`/health` mostra o banco) |
| `front` | Interface em **http://localhost:8080**. O nginx repassa `/api` para a API |

Entre no front com o `ADMIN_EMAIL` e a `ADMIN_SENHA` do `.env`. O seed é idempotente: se já existe um administrador, nada é criado nem alterado. Para outra porta, use `PORT` (API) ou `FRONT_PORT` (front) no `.env`.

Para parar: `docker compose down`. Os dados ficam no volume `mssql-data`; `docker compose down -v` apaga tudo.

### Desenvolvimento

Para rodar a API fora do Docker, com recarga automática, deixe só o banco no compose:

```bash
npm ci
docker compose up -d --wait db db-init
npm run migration:run
npm run seed:admin
npm run start:dev
```

A documentação da API (Swagger) fica em http://localhost:3000/docs. Ela só existe fora de `NODE_ENV=production`, então não aparece no container.

## Testes

| Comando | O que roda |
|---|---|
| `npm run verificar` | Prettier, ESLint, TypeScript e os testes unitários (`src/**/*.spec.ts`). Não precisa de banco |
| `npm run test:e2e` | Testes e2e (`test/*.e2e-spec.ts`) com o app inteiro contra o SQL Server do compose |

Os e2e usam um database próprio, `<DB_NAME>_e2e`, no mesmo servidor. Os dados de desenvolvimento não são tocados. Na primeira execução, o setup cria o database e o schema e aplica as migrations. Cada teste começa com as tabelas vazias. Antes de rodar, o banco precisa estar de pé (`docker compose up -d --wait db db-init`).

## Migrations

```bash
npm run migration:run       # aplica as pendentes
npm run migration:revert    # desfaz a última
npm run migration:show      # lista o estado
npm run migration:create -- src/infrastructure/database/migrations/NomeDaMigration
```

O TypeORM nunca sincroniza o schema sozinho (`synchronize: false`). Toda mudança de tabela passa por uma migration.

## Estrutura

```
src/
  core/              configuração (env validada), filtro de erros, pipe de validação
  infrastructure/    banco (TypeORM, migrations, seed) e geração de PDF
  modules/
    acesso/          login (JWT), usuários e papéis, registro de acesso
    alertas/         parâmetros de alerta, histórico de alterações e alertas
    rastreio-operacional/  ações, linha do tempo e tempo de acionamento
    boletins/        pré-visualização em HTML e PDF do boletim
    health/          GET /health
test/                e2e e seus helpers
```

## Formato de erro

Todo erro responde em JSON:

```json
{ "status_code": 409, "error": "Conflict", "message": "Já existe um usuário com este e-mail",
  "business_rule_code": "EMAIL_JA_CADASTRADO", "timestamp": "...", "path": "/usuarios" }
```

Dados inválidos respondem 422, com `message: "Dados inválidos"` e o detalhe por campo em `errors`.
