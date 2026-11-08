# VigiaClima-Recife

O projeto separa a extração para MongoDB da publicação da camada Bronze no
Azure Blob Storage.

```text
projeto_5/
├── mongo/                 # Coletores, configuração e persistência MongoDB
│   ├── collectors/
│   ├── database/mongodb.py
│   ├── utils/
│   ├── main.py
│   └── requirements.txt
├── bronze/                # Cliente Azure e exportação em tabelas Parquet
│   ├── azure_blob.py
│   ├── pipeline.py
│   ├── main.py
│   ├── tests/
│   └── requirements.txt
├── silver/                # Carga piloto SQL Server e orquestração Silver
│   ├── database/sql_server.py
│   ├── pipelines/
│   ├── tests/
│   └── requirements.txt
├── sql/                    # DDL idempotente de staging e Silver
├── .env                   # Configuração local, ignorada pelo Git
└── .env.example           # Modelo sem credenciais
```

## Configuração

Copie `.env.example` para `.env` e preencha `MONGODB_URI`, `AZURE_TENANT_ID`,
`AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET`. O arquivo `.env` está no
`.gitignore`. `MONGODB_DATABASE`, `AZURE_STORAGE_ACCOUNT_URL` e
`AZURE_STORAGE_CONTAINER` já têm valores padrão no modelo.

Instale as dependências de cada etapa na raiz `projeto_5`:

```bash
python3 -m pip install -r mongo/requirements.txt
python3 -m pip install -r bronze/requirements.txt
```

## Executar

Extração das fontes e persistência no MongoDB:

```bash
python3 -m mongo.main
```

Exportação das coleções atuais do MongoDB para Parquet no Azure:

```bash
python3 -m bronze.main
```

As etapas são independentes. Rode a extração antes da Bronze quando quiser
publicar os dados recém-coletados. Cada coleção é uma tabela lógica no
container `vigia-bronze`, particionada por ano, mês e dia da exportação. Os
arquivos `.parquet` preservam o documento BSON original em Extended JSON.

Para testar somente a autenticação e o upload de validação:

```bash
python3 -m bronze.tests.test_azure_connection
```

Testes unitários da exportação:

```bash
python3 -m unittest discover -s bronze/tests -v
```

## Piloto da camada Silver (INMET estações)

A pasta `silver/` contém o carregador para staging, a conexão Python com SQL
Server e a procedure piloto. O piloto processa somente Parquets em
`inmet/estacoes/`: no container atual foi encontrado um arquivo real com 16
linhas. Ainda não existe Parquet em `inmet/observacoes/`; essa tabela e as
outras fontes ficam fora do piloto para não presumir seus dados.

O conector usa o driver oficial `mssql-python`, que inclui seus componentes de
conexão e dispensa instalação manual do ODBC 18 no macOS. O modo é selecionado
por `SQL_AUTH_MODE`: `ActiveDirectoryInteractive` para MFA,
`ActiveDirectoryServicePrincipal` para aplicação, ou `SqlPassword`. Se o modo
for omitido, credenciais SQL completas selecionam `SqlPassword`; sem elas, o
login interativo com MFA é o padrão. Os segredos permanecem no `.env` e não são
registrados nos logs. `SQL_DRIVER` é mantido no exemplo para compatibilidade com
configurações antigas, mas não é usado pelo driver Microsoft.

Instale as dependências em um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r silver/requirements.txt
```

O teste independente, que apenas conecta e executa uma consulta `SELECT`, roda
da raiz `projeto_5` com:

```bash
python3 -m silver.test_sql_connection
```

Ele informa se o driver está disponível, usa o modo selecionado e, se conectar,
mostra database, usuário e horário retornados pelo SQL Server.

Instale os requisitos do piloto e execute a partir desta pasta:

```bash
python -m silver.main
```

Na primeira execução, scripts idempotentes criam apenas os objetos ausentes
`staging.INMET_Estacoes`, `staging.ArquivosProcessados`,
`staging.Rejeitados`, `silver.INMET_Estacoes`, `silver.Execucoes` e
`silver.sp_tratar_inmet`. Nenhuma tabela existente é apagada ou truncada. A
procedure preserva os valores recebidos, rejeita apenas `_id` vazio ou
JSON inválido (`documento_json` ou `payload_json`) e evita duplicar IDs na
tabela Silver.

O usuário SQL precisa de permissão para criar os objetos na primeira execução.
Se o pipeline informar `CREATE TABLE permission denied`, um administrador do
database deve conceder as permissões abaixo a `vigia_operator`:

```sql
GRANT CREATE TABLE TO [vigia_operator];
GRANT CREATE PROCEDURE TO [vigia_operator];
GRANT ALTER ON SCHEMA::staging TO [vigia_operator];
GRANT ALTER ON SCHEMA::silver TO [vigia_operator];
GRANT SELECT, INSERT, UPDATE ON SCHEMA::staging TO [vigia_operator];
GRANT SELECT, INSERT, UPDATE ON SCHEMA::silver TO [vigia_operator];
GRANT EXECUTE ON SCHEMA::silver TO [vigia_operator];
```

Os Parquets reais do Azure foram lidos e seu schema foi conferido. A carga real
no SQL Server depende do acesso de rede e das credenciais configuradas no `.env`.
O comando de teste local é:

```bash
python3 -m unittest discover -s silver/tests -v
```
