-- Camada Gold: dados prontos para consumo pelo app VijaClima.
-- Script idempotente — pode ser re-executado sem erro.

IF SCHEMA_ID(N'gold') IS NULL EXEC(N'CREATE SCHEMA gold');
GO

-- -----------------------------------------------------------------------
-- Migração: recria gold.leitura_climatica se ainda estiver no formato longo
-- (coluna "variavel"). O formato atual é largo: uma coluna por variável.
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'gold.leitura_climatica', N'U') IS NOT NULL
   AND EXISTS (
       SELECT 1 FROM sys.columns
       WHERE object_id = OBJECT_ID(N'gold.leitura_climatica')
         AND name = N'variavel'
   )
BEGIN
    DROP TABLE gold.leitura_climatica;
END
GO

-- -----------------------------------------------------------------------
-- gold.leitura_climatica
-- Formato largo: uma linha por (fonte, estacao, lida_em).
-- Cada variável climática ocupa sua própria coluna NULL (pode não estar
-- disponível em todas as fontes para todos os horários).
-- Chave: (fonte, estacao, lida_em).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'gold.leitura_climatica', N'U') IS NULL
CREATE TABLE gold.leitura_climatica (
    id              INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_gold_leitura_climatica      PRIMARY KEY,
    fonte           NVARCHAR(50)       NOT NULL,
    estacao         NVARCHAR(100)      NOT NULL,
    territorio      NVARCHAR(100)      NOT NULL,
    lida_em         DATETIMEOFFSET(6)  NOT NULL,
    natureza_dado   NVARCHAR(50)       NULL,
    temperatura_c   FLOAT              NULL,
    precipitacao_mm FLOAT              NULL,
    umidade_pct     FLOAT              NULL,
    pressao_hpa     FLOAT              NULL,
    atualizado_em   DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_gold_leitura_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_gold_leitura_climatica UNIQUE (fonte, estacao, lida_em)
);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_gold_leitura_climatica_lida_em'
      AND object_id = OBJECT_ID(N'gold.leitura_climatica')
)
CREATE INDEX IX_gold_leitura_climatica_lida_em
    ON gold.leitura_climatica (lida_em DESC)
    INCLUDE (fonte, estacao, territorio, natureza_dado,
             temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa);
GO

-- -----------------------------------------------------------------------
-- gold.estacao
-- Metadados das estações (origem: silver.Estacoes / INMET).
-- Mantida no schema para uso futuro; população suspensa enquanto
-- silver.Estacoes não receber dados do INMET.
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
-- gold.v_clima_periodo (VIEW)
-- Agrega leitura_climatica (horária) em duas granularidades:
--   • semanal YYYY-WNN  → para JOIN com arboviroses e SINAN
--   • mensal  YYYY-MM   → para JOIN com defesa civil
-- Uma linha por (territorio, periodo) em cada granularidade.
-- precipitacao_mm é somada (chuva acumulada); demais variáveis são médias.
-- -----------------------------------------------------------------------
CREATE OR ALTER VIEW gold.v_clima_periodo AS
-- Agregação semanal (formato "2026-W44")
SELECT
    territorio,
    CAST(DATEPART(YEAR,     lida_em) AS NVARCHAR(4))
        + N'-W'
        + RIGHT(N'0' + CAST(DATEPART(ISO_WEEK, lida_em) AS NVARCHAR(2)), 2) AS periodo,
    AVG(temperatura_c)   AS avg_temperatura_c,
    SUM(precipitacao_mm) AS sum_precipitacao_mm,
    AVG(umidade_pct)     AS avg_umidade_pct,
    AVG(pressao_hpa)     AS avg_pressao_hpa,
    COUNT(*)             AS n_leituras
FROM gold.leitura_climatica
GROUP BY
    territorio,
    CAST(DATEPART(YEAR,     lida_em) AS NVARCHAR(4))
        + N'-W'
        + RIGHT(N'0' + CAST(DATEPART(ISO_WEEK, lida_em) AS NVARCHAR(2)), 2)

UNION ALL

-- Agregação mensal (formato "2026-11")
SELECT
    territorio,
    FORMAT(lida_em, 'yyyy-MM') AS periodo,
    AVG(temperatura_c),
    SUM(precipitacao_mm),
    AVG(umidade_pct),
    AVG(pressao_hpa),
    COUNT(*)
FROM gold.leitura_climatica
GROUP BY territorio, FORMAT(lida_em, 'yyyy-MM');
GO

-- -----------------------------------------------------------------------
-- gold.v_correlacao (VIEW)
-- Cruza indicador_territorio com v_clima_periodo pelo período.
-- Uma linha por (bairro, indicador, periodo) com clima agregado ao lado.
-- Para SINAN (territorio=Pernambuco), usa Recife como proxy climático
-- já que a coleta cobre apenas a capital.
-- -----------------------------------------------------------------------
CREATE OR ALTER VIEW gold.v_correlacao AS
SELECT
    i.territorio,
    i.bairro,
    i.indicador,
    i.periodo,
    i.valor                 AS casos,
    i.fonte                 AS fonte_indicador,
    c.avg_temperatura_c,
    c.sum_precipitacao_mm,
    c.avg_umidade_pct,
    c.avg_pressao_hpa,
    c.n_leituras            AS n_leituras_clima
FROM gold.indicador_territorio i
LEFT JOIN gold.v_clima_periodo c
    ON  c.territorio = CASE
                           WHEN i.territorio = N'Pernambuco' THEN N'Recife'
                           ELSE i.territorio
                       END
    AND c.periodo    = i.periodo;
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
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.recife_samu
    UNION ALL
    SELECT fonte, ingestao_ts FROM bronze.recife_acidentes_transito
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
