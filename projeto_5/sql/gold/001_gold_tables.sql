-- Camada Gold: dados prontos para consumo pelo app VijaClima.
-- Script idempotente — pode ser re-executado sem erro.

IF SCHEMA_ID(N'gold') IS NULL EXEC(N'CREATE SCHEMA gold');
GO

-- -----------------------------------------------------------------------
-- gold.leitura_climatica
-- Uma linha por variável medida, em formato longo (UNPIVOT de silver.Meteorologia).
-- Chave: (fonte, estacao, variavel, lida_em).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'gold.leitura_climatica', N'U') IS NULL
CREATE TABLE gold.leitura_climatica (
    id              INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_gold_leitura_climatica      PRIMARY KEY,
    fonte           NVARCHAR(50)       NOT NULL,
    estacao         NVARCHAR(100)      NOT NULL,
    territorio      NVARCHAR(100)      NOT NULL,
    variavel        NVARCHAR(50)       NOT NULL,
    valor           FLOAT              NOT NULL,
    lida_em         DATETIMEOFFSET(6)  NOT NULL,
    natureza_dado   NVARCHAR(50)       NULL,
    atualizado_em   DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_gold_leitura_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_gold_leitura_climatica UNIQUE (fonte, estacao, variavel, lida_em)
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_gold_leitura_climatica_lida_em'
      AND object_id = OBJECT_ID(N'gold.leitura_climatica')
)
CREATE INDEX IX_gold_leitura_climatica_lida_em
    ON gold.leitura_climatica (lida_em DESC)
    INCLUDE (fonte, estacao, territorio, variavel, valor, natureza_dado);
GO

-- -----------------------------------------------------------------------
-- gold.estacao
-- Metadados das estações (origem: silver.Estacoes / INMET).
-- Chave: (fonte, estacao).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'gold.estacao', N'U') IS NULL
CREATE TABLE gold.estacao (
    id            INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_gold_estacao      PRIMARY KEY,
    fonte         NVARCHAR(50)       NOT NULL,
    estacao       NVARCHAR(100)      NOT NULL,
    nome          NVARCHAR(200)      NULL,
    municipio     NVARCHAR(200)      NULL,
    latitude      FLOAT              NULL,
    longitude     FLOAT              NULL,
    situacao      NVARCHAR(50)       NULL,
    atualizado_em DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_gold_estacao_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_gold_estacao UNIQUE (fonte, estacao)
);
GO

-- -----------------------------------------------------------------------
-- gold.indicador_territorio
-- Contagens epidemiológicas e de ocorrências por bairro e período.
-- Chave: (territorio, bairro, indicador, periodo, fonte).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'gold.indicador_territorio', N'U') IS NULL
CREATE TABLE gold.indicador_territorio (
    id            INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_gold_indicador_territorio      PRIMARY KEY,
    territorio    NVARCHAR(100)      NOT NULL,
    bairro        NVARCHAR(200)      NOT NULL,
    indicador     NVARCHAR(300)      NOT NULL,
    valor         INT                NOT NULL,
    periodo       NVARCHAR(20)       NOT NULL,
    fonte         NVARCHAR(50)       NOT NULL,
    atualizado_em DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_gold_indicador_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_gold_indicador_territorio UNIQUE (territorio, bairro, indicador, periodo, fonte)
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_gold_indicador_territorio_periodo'
      AND object_id = OBJECT_ID(N'gold.indicador_territorio')
)
CREATE INDEX IX_gold_indicador_territorio_periodo
    ON gold.indicador_territorio (periodo DESC, territorio, indicador);
GO

-- -----------------------------------------------------------------------
-- gold.fonte_status (VIEW — sempre atual, sem dados duplicados)
-- Última ingestão de cada fonte a partir das tabelas bronze.
-- -----------------------------------------------------------------------
CREATE OR ALTER VIEW gold.fonte_status AS
SELECT
    fonte,
    MAX(ingestao_ts) AS ultima_atualizacao
FROM (
    SELECT fonte, ingestao_ts FROM bronze.inmet_estacoes
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.openmeteo_horario
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.openmeteo_historico
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.nasa_power_horario
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.recife_arboviroses
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.recife_defesa_civil
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.sinan_animais_peconhentos
) AS todas
GROUP BY fonte;
GO

-- -----------------------------------------------------------------------
-- Usuário somente-leitura para o app (executar com permissão de administrador)
-- -----------------------------------------------------------------------
-- CREATE USER vigia_app WITH PASSWORD = 'TrocaEstaS3nha!';
-- GRANT SELECT ON SCHEMA::gold TO vigia_app;
-- DENY  SELECT ON SCHEMA::bronze TO vigia_app;
-- DENY  SELECT ON SCHEMA::silver TO vigia_app;
-- GO
