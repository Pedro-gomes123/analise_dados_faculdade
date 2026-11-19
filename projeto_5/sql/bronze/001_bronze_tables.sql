-- Camada Bronze: schema e tabelas de aterrissagem dos dados brutos do MongoDB.
-- Script idempotente — pode ser re-executado sem erro.

IF SCHEMA_ID(N'bronze') IS NULL EXEC(N'CREATE SCHEMA bronze');
GO

-- Tabela de controle de exportações (uma linha por execução de pipeline)
IF OBJECT_ID(N'bronze.ExportacoesLog', N'U') IS NULL
CREATE TABLE bronze.ExportacoesLog (
    id              INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_bronze_ExportacoesLog PRIMARY KEY,
    colecao         NVARCHAR(100)      NOT NULL,
    tabela          NVARCHAR(200)      NOT NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL,
    documentos      INT                NOT NULL CONSTRAINT DF_bronze_Log_documentos  DEFAULT (0),
    inseridos       INT                NOT NULL CONSTRAINT DF_bronze_Log_inseridos   DEFAULT (0)
);
GO

-- Macro: todas as tabelas de dados têm a mesma estrutura base.
-- _id = SHA-256 hex gerado pelo MongoDB (64 chars); garante idempotência.

IF OBJECT_ID(N'bronze.inmet_estacoes', N'U') IS NULL
CREATE TABLE bronze.inmet_estacoes (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_inmet_estacoes          PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_inmet_estacoes_exp       DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.openmeteo_horario', N'U') IS NULL
CREATE TABLE bronze.openmeteo_horario (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_openmeteo_horario      PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_openmeteo_horario_exp  DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.openmeteo_historico', N'U') IS NULL
CREATE TABLE bronze.openmeteo_historico (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_openmeteo_historico    PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_openmeteo_historico_exp DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.nasa_power_horario', N'U') IS NULL
CREATE TABLE bronze.nasa_power_horario (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_nasa_power_horario     PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_nasa_power_horario_exp  DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.recife_arboviroses', N'U') IS NULL
CREATE TABLE bronze.recife_arboviroses (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_recife_arboviroses     PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_recife_arboviroses_exp  DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.recife_defesa_civil', N'U') IS NULL
CREATE TABLE bronze.recife_defesa_civil (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_recife_defesa_civil    PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_recife_defesa_civil_exp DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.sinan_animais_peconhentos', N'U') IS NULL
CREATE TABLE bronze.sinan_animais_peconhentos (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_sinan_animais          PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_sinan_animais_exp       DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.recife_samu', N'U') IS NULL
CREATE TABLE bronze.recife_samu (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_recife_samu             PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_recife_samu_exp          DEFAULT SYSDATETIMEOFFSET()
);
GO

IF OBJECT_ID(N'bronze.recife_acidentes_transito', N'U') IS NULL
CREATE TABLE bronze.recife_acidentes_transito (
    [_id]           NVARCHAR(64)       NOT NULL CONSTRAINT PK_bronze_recife_acidentes        PRIMARY KEY,
    fonte           NVARCHAR(100)      NULL,
    tipo_dado       NVARCHAR(100)      NULL,
    municipio       NVARCHAR(200)      NULL,
    ingestao_ts     DATETIMEOFFSET(6)  NULL,
    payload_json    NVARCHAR(MAX)      NULL,
    documento_json  NVARCHAR(MAX)      NULL,
    exportado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_bronze_recife_acidentes_exp     DEFAULT SYSDATETIMEOFFSET()
);
GO
