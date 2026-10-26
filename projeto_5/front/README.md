# O Vigia: front

Interface da Sala de Situação do Vigidesastres. React 19 + TypeScript, com Vite, TanStack Router e Query, Tailwind e shadcn/ui.

Cada usuário vê só as estações dos seus papéis:

| Estação | Papel |
|---|---|
| EST-01 · Técnico(a) Vigidesastres | TEC |
| EST-02 · Gestor(a) de Emergências: alertas, parâmetros, registro de ações e linha do tempo | GES |
| EST-03 · Gestão Institucional: tempo médio de acionamento | GIN |
| EST-04 · Comunicação Institucional: composição, pré-visualização e PDF do boletim | COM |
| Usuários: contas e papéis | ADM |

## Requisitos

- **Node 22** (`.nvmrc`).
- **A API rodando** em http://localhost:3000. Veja `../back/README.md`.

## Rodar

Para subir o sistema inteiro (banco, API e front, em http://localhost:8080), use o `docker compose` do back. Veja `../back/README.md`.

Para desenvolver o front com recarga automática, com a API de pé, rode nesta pasta (`projeto_5/front`):

```bash
npm ci
npm run dev    # http://localhost:5173
```

Entre com o administrador criado pelo `npm run seed:admin` do back e crie os demais usuários na tela **Usuários**.

As chamadas vão para `/api`. Em desenvolvimento, o Vite repassa esse caminho para `http://localhost:3000` sem o prefixo (`vite.config.ts`). Para outra URL, defina `VITE_API_URL` em um `.env` (modelo em `.env.example`).

## Comandos

| Comando | O que faz |
|---|---|
| `npm run verificar` | oxlint, TypeScript e testes (Vitest + Testing Library) |
| `npm run build` | Build de produção em `dist/` |
| `npm run preview` | Serve o build localmente |

No Docker, o build é servido pelo nginx (`Dockerfile`, `nginx.conf`), que repassa `/api` para a API como o proxy do Vite.

## Estrutura

```
src/
  components/      componentes reutilizáveis (ui/ = shadcn/ui; layout/ = menu lateral e cabeçalho)
  lib/             cliente HTTP, formatação de datas e números, períodos
  modules/         uma pasta por assunto: service (API), hooks (Query), components
  routes/          rotas por arquivo (TanStack Router); _autenticado/ exige login
  test/            helpers dos testes
```
