-- Camada Silver: dados limpos e estruturados a partir das tabelas bronze.
-- Script idempotente — pode ser re-executado sem erro.

IF SCHEMA_ID(N'silver') IS NULL EXEC(N'CREATE SCHEMA silver');
GO

-- -----------------------------------------------------------------------
-- silver.Meteorologia
-- Unifica openmeteo_horario, openmeteo_historico e nasa_power_horario.
-- Chave de negócio: (fonte, lida_em) — uma leitura por hora por fonte.
-- Pressão normalizada para hPa (NASA POWER usa kPa; conversão no pipeline).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'silver.Meteorologia', N'U') IS NULL
CREATE TABLE silver.Meteorologia (
    id              INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_silver_Meteorologia      PRIMARY KEY,
    fonte           NVARCHAR(50)       NOT NULL,
    estacao         NVARCHAR(100)      NOT NULL,
    territorio      NVARCHAR(100)      NOT NULL,
    lida_em         DATETIMEOFFSET(6)  NOT NULL,
    natureza_dado   NVARCHAR(50)       NULL,
    temperatura_c   FLOAT              NULL,
    precipitacao_mm FLOAT              NULL,
    umidade_pct     FLOAT              NULL,
    pressao_hpa     FLOAT              NULL,
    vento_ms        FLOAT              NULL,
    latitude        FLOAT              NULL,
    longitude       FLOAT              NULL,
    atualizado_em   DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_silver_Met_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_silver_Meteorologia UNIQUE (fonte, lida_em)
);
GO

-- -----------------------------------------------------------------------
-- silver.Arboviroses
-- Casos semanais agregados de dengue, zika e chikungunya em Recife.
-- Chave: (indicador, periodo, bairro).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'silver.Arboviroses', N'U') IS NULL
CREATE TABLE silver.Arboviroses (
    id          INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_silver_Arboviroses   PRIMARY KEY,
    territorio  NVARCHAR(100)      NOT NULL,
    bairro      NVARCHAR(200)      NOT NULL,
    indicador   NVARCHAR(50)       NOT NULL,
    periodo     NVARCHAR(10)       NOT NULL,
    casos       INT                NOT NULL,
    atualizado_em DATETIMEOFFSET(6) NOT NULL CONSTRAINT DF_silver_Arb_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_silver_Arboviroses UNIQUE (territorio, indicador, periodo, bairro)
);
GO

-- -----------------------------------------------------------------------
-- silver.DefesaCivil
-- Atendimentos mensais da Defesa Civil do Recife por tipo e bairro.
-- Chave: (tipo_ocorrencia, periodo, bairro).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'silver.DefesaCivil', N'U') IS NULL
CREATE TABLE silver.DefesaCivil (
    id               INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_silver_DefesaCivil   PRIMARY KEY,
    territorio       NVARCHAR(100)      NOT NULL,
    bairro           NVARCHAR(200)      NOT NULL,
    tipo_ocorrencia  NVARCHAR(300)      NOT NULL,
    periodo          NVARCHAR(10)       NOT NULL,
    casos            INT                NOT NULL,
    atualizado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_silver_DC_atualizado  DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_silver_DefesaCivil UNIQUE (territorio, tipo_ocorrencia, periodo, bairro)
);
GO

-- -----------------------------------------------------------------------
-- silver.AnimaisPerconhentos
-- Acidentes semanais com animais peçonhentos em Pernambuco por município.
-- Chave: (municipio, codigo_municipio, periodo).
-- -----------------------------------------------------------------------
-- -----------------------------------------------------------------------
-- silver.Estacoes
-- Metadados das estações meteorológicas (origem: INMET via bronze).
-- Chave: (fonte, estacao).
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'silver.Estacoes', N'U') IS NULL
CREATE TABLE silver.Estacoes (
    id            INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_silver_Estacoes      PRIMARY KEY,
    fonte         NVARCHAR(50)       NOT NULL,
    estacao       NVARCHAR(100)      NOT NULL,
    nome          NVARCHAR(200)      NULL,
    municipio     NVARCHAR(200)      NULL,
    latitude      FLOAT              NULL,
    longitude     FLOAT              NULL,
    situacao      NVARCHAR(50)       NULL,
    atualizado_em DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_silver_Est_atualizado DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_silver_Estacoes UNIQUE (fonte, estacao)
);
GO

IF OBJECT_ID(N'silver.AnimaisPerconhentos', N'U') IS NULL
CREATE TABLE silver.AnimaisPerconhentos (
    id               INT IDENTITY(1,1)  NOT NULL CONSTRAINT PK_silver_Animais        PRIMARY KEY,
    territorio       NVARCHAR(100)      NOT NULL,
    municipio        NVARCHAR(200)      NOT NULL,
    codigo_municipio NVARCHAR(20)       NOT NULL,
    periodo          NVARCHAR(10)       NOT NULL,
    casos            INT                NOT NULL,
    atualizado_em    DATETIMEOFFSET(6)  NOT NULL CONSTRAINT DF_silver_Ani_atualizado  DEFAULT SYSDATETIMEOFFSET(),
    CONSTRAINT UQ_silver_AnimaisPerconhentos UNIQUE (territorio, municipio, codigo_municipio, periodo)
);
GO
