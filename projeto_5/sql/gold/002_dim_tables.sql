-- Tabelas Dimensão — enriquecimento analítico da camada gold.
-- Script idempotente — pode ser re-executado sem erro.
-- Executar APÓS 001_gold_tables.sql (depende do schema gold).

-- -----------------------------------------------------------------------
-- dim.Tempo (calendário 2018–2030)
-- Permite agrupar leitura_climatica e indicador_territorio por semana,
-- mês, estação do ano etc. sem precisar recalcular no app.
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'dim.Tempo', N'U') IS NULL
BEGIN
    IF SCHEMA_ID(N'dim') IS NULL EXEC(N'CREATE SCHEMA dim');

    CREATE TABLE dim.Tempo (
        id              INT            NOT NULL CONSTRAINT PK_dim_Tempo PRIMARY KEY,
        data            DATE           NOT NULL CONSTRAINT UQ_dim_Tempo_data UNIQUE,
        dia_semana      TINYINT        NOT NULL, -- 1=Domingo … 7=Sábado (padrão SQL Server)
        nome_dia        NVARCHAR(15)   NOT NULL,
        semana_iso      TINYINT        NOT NULL, -- semana ISO 8601 (1–53)
        ano_semana_iso  SMALLINT       NOT NULL, -- ano da semana ISO (pode diferir do ano calendário)
        mes             TINYINT        NOT NULL,
        nome_mes        NVARCHAR(15)   NOT NULL,
        trimestre       TINYINT        NOT NULL,
        ano             SMALLINT       NOT NULL,
        estacao         NVARCHAR(12)   NOT NULL, -- Verão / Outono / Inverno / Primavera
        is_fim_semana   BIT            NOT NULL
    );
END;
GO

-- Popula dim.Tempo com datas de 2018 a 2030 (caso ainda não existam).
-- MAXRECURSION 5000 cobre ~4.748 dias; ajuste se ampliar o intervalo.
IF NOT EXISTS (SELECT 1 FROM dim.Tempo WHERE data = '2018-01-01')
BEGIN
    ;WITH datas AS (
        SELECT CAST('2018-01-01' AS DATE) AS d, 1 AS seq
        UNION ALL
        SELECT DATEADD(DAY, 1, d), seq + 1
        FROM datas
        WHERE d < '2030-12-31'
    )
    INSERT INTO dim.Tempo
        (id, data, dia_semana, nome_dia, semana_iso, ano_semana_iso,
         mes, nome_mes, trimestre, ano, estacao, is_fim_semana)
    SELECT
        seq                                AS id,
        d                                  AS data,
        DATEPART(WEEKDAY, d)               AS dia_semana,
        DATENAME(WEEKDAY, d)               AS nome_dia,
        DATEPART(ISO_WEEK, d)              AS semana_iso,
        -- Ano da semana ISO: a semana 1 pode pertencer ao ano anterior/seguinte
        YEAR(DATEADD(DAY, 26 - DATEPART(ISO_WEEK, d), d))
                                           AS ano_semana_iso,
        MONTH(d)                           AS mes,
        DATENAME(MONTH, d)                 AS nome_mes,
        DATEPART(QUARTER, d)               AS trimestre,
        YEAR(d)                            AS ano,
        -- Estações astronômicas do Hemisfério Sul (simplificadas por mês)
        CASE
            WHEN MONTH(d) IN (12, 1, 2) THEN N'Verão'
            WHEN MONTH(d) IN (3, 4, 5)  THEN N'Outono'
            WHEN MONTH(d) IN (6, 7, 8)  THEN N'Inverno'
            ELSE                              N'Primavera'
        END                                AS estacao,
        CASE WHEN DATEPART(WEEKDAY, d) IN (1, 7) THEN 1 ELSE 0 END
                                           AS is_fim_semana
    FROM datas
    OPTION (MAXRECURSION 5000);
END;
GO

-- -----------------------------------------------------------------------
-- dim.Territorio (hierarquia geográfica de Recife)
-- Vincula bairros às Regiões Político-Administrativas (RPAs) e
-- coordenadas aproximadas do centroide.
-- Popule com o GeoJSON de bairros de Dados Abertos Recife para ter
-- geometria completa e população IBGE 2022.
-- -----------------------------------------------------------------------
IF SCHEMA_ID(N'dim') IS NULL EXEC(N'CREATE SCHEMA dim');
GO

IF OBJECT_ID(N'dim.Territorio', N'U') IS NULL
CREATE TABLE dim.Territorio (
    id                  INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_Territorio PRIMARY KEY,
    bairro              NVARCHAR(200)     NOT NULL CONSTRAINT UQ_dim_Territorio_bairro UNIQUE,
    rpa                 NVARCHAR(10)      NULL,  -- RPA1 … RPA6
    nome_rpa            NVARCHAR(100)     NULL,
    municipio           NVARCHAR(100)     NOT NULL DEFAULT N'Recife',
    estado              NCHAR(2)          NOT NULL DEFAULT N'PE',
    latitude_centroide  FLOAT             NULL,
    longitude_centroide FLOAT             NULL,
    area_km2            FLOAT             NULL,
    populacao_2022      INT               NULL   -- Censo IBGE 2022
);
GO

-- Seed das 6 RPAs (Regiões Político-Administrativas do Recife)
-- Referência: Lei 17.365/2007 – Plano Diretor do Recife
IF NOT EXISTS (SELECT 1 FROM dim.Territorio WHERE bairro = N'RPA1 - Centro')
INSERT INTO dim.Territorio (bairro, rpa, nome_rpa, municipio, estado)
VALUES
    (N'RPA1 - Centro',    N'RPA1', N'Centro',    N'Recife', N'PE'),
    (N'RPA2 - Norte',     N'RPA2', N'Norte',     N'Recife', N'PE'),
    (N'RPA3 - Noroeste',  N'RPA3', N'Noroeste',  N'Recife', N'PE'),
    (N'RPA4 - Oeste',     N'RPA4', N'Oeste',     N'Recife', N'PE'),
    (N'RPA5 - Sudoeste',  N'RPA5', N'Sudoeste',  N'Recife', N'PE'),
    (N'RPA6 - Sul',       N'RPA6', N'Sul',       N'Recife', N'PE');
GO

-- -----------------------------------------------------------------------
-- dim.Indicador (catálogo de indicadores com limiares de alerta)
-- Define categoria, unidade e thresholds de alerta/crítico para cada
-- variável. Usado pelo app para classificar leituras e disparar alertas.
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'dim.Indicador', N'U') IS NULL
CREATE TABLE dim.Indicador (
    id               INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_Indicador PRIMARY KEY,
    indicador        NVARCHAR(100)     NOT NULL CONSTRAINT UQ_dim_Indicador UNIQUE,
    categoria        NVARCHAR(30)      NOT NULL, -- climatico / saude / desastre
    nome_completo    NVARCHAR(200)     NOT NULL,
    unidade          NVARCHAR(30)      NULL,
    descricao        NVARCHAR(500)     NULL,
    limite_alerta    FLOAT             NULL,     -- valor acima (ou abaixo) que gera alerta
    limite_critico   FLOAT             NULL,     -- valor acima (ou abaixo) que gera alerta crítico
    sentido_alerta   NVARCHAR(5)       NULL      -- 'acima' ou 'abaixo'
);
GO

-- Seed dos indicadores conhecidos do sistema
IF NOT EXISTS (SELECT 1 FROM dim.Indicador WHERE indicador = N'temperatura_c')
INSERT INTO dim.Indicador
    (indicador, categoria, nome_completo, unidade, descricao, limite_alerta, limite_critico, sentido_alerta)
VALUES
    -- Variáveis climáticas (gold.leitura_climatica)
    (N'temperatura_c',   N'climatico', N'Temperatura do Ar',           N'°C',    N'Temperatura medida a 2 m de altura.',    35.0, 38.0, N'acima'),
    (N'precipitacao_mm', N'climatico', N'Precipitação Horária',        N'mm/h',  N'Volume de chuva acumulado na hora.',      10.0, 30.0, N'acima'),
    (N'umidade_pct',     N'climatico', N'Umidade Relativa do Ar',      N'%',     N'Umidade relativa medida a 2 m.',          NULL, NULL, NULL    ),
    (N'pressao_hpa',     N'climatico', N'Pressão Atmosférica',         N'hPa',   N'Pressão ao nível da superfície.',         NULL, NULL, NULL    ),
    (N'vento_ms',        N'climatico', N'Velocidade do Vento',         N'm/s',   N'Velocidade do vento a 10 m de altura.',   15.0, 20.0, N'acima'),
    -- Saúde (gold.indicador_territorio)
    (N'dengue',          N'saude',     N'Casos de Dengue',             N'casos', N'Notificações semanais de dengue (SINAN).', NULL, NULL, NULL   ),
    (N'zika',            N'saude',     N'Casos de Zika',               N'casos', N'Notificações semanais de Zika (SINAN).',   NULL, NULL, NULL   ),
    (N'chikungunya',     N'saude',     N'Casos de Chikungunya',        N'casos', N'Notificações semanais de chikungunya.',    NULL, NULL, NULL   ),
    (N'acidentes_animais_peconhentos', N'saude',
                                       N'Acidentes com Animais Peçonhentos', N'casos',
                                       N'Notificações semanais SINAN ANIM — Pernambuco.', NULL, NULL, NULL),
    -- Desastres / Defesa Civil (tipos mais comuns; novos tipos são inseridos automaticamente)
    (N'Deslizamento',    N'desastre',  N'Deslizamento de Terra',       N'ocorr.', N'Atendimento da Defesa Civil do Recife.',  NULL, NULL, NULL   ),
    (N'Alagamento',      N'desastre',  N'Alagamento / Enchente',       N'ocorr.', N'Atendimento da Defesa Civil do Recife.',  NULL, NULL, NULL   );
GO

-- -----------------------------------------------------------------------
-- dim.Fonte (catálogo de fontes de dados)
-- Registra metadados operacionais de cada API: organização, URL base,
-- frequência de coleta, cobertura geográfica e se requer autenticação.
-- -----------------------------------------------------------------------
IF OBJECT_ID(N'dim.Fonte', N'U') IS NULL
CREATE TABLE dim.Fonte (
    id                     INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_Fonte PRIMARY KEY,
    fonte                  NVARCHAR(50)      NOT NULL CONSTRAINT UQ_dim_Fonte UNIQUE,
    nome_completo          NVARCHAR(200)     NOT NULL,
    organizacao            NVARCHAR(200)     NULL,
    url_base               NVARCHAR(500)     NULL,
    frequencia_coleta      NVARCHAR(50)      NULL,  -- horaria / diaria / semanal / mensal
    cobertura_geografica   NVARCHAR(100)     NULL,
    licenca                NVARCHAR(100)     NULL,
    requer_autenticacao    BIT               NOT NULL DEFAULT 0,
    notas                  NVARCHAR(1000)    NULL
);
GO

IF NOT EXISTS (SELECT 1 FROM dim.Fonte WHERE fonte = N'openmeteo')
INSERT INTO dim.Fonte
    (fonte, nome_completo, organizacao, url_base, frequencia_coleta,
     cobertura_geografica, licenca, requer_autenticacao, notas)
VALUES
    (N'openmeteo',
     N'Open-Meteo Forecast',
     N'Open-Meteo GmbH',
     N'https://api.open-meteo.com/v1/forecast',
     N'horaria',
     N'Global (ponto Recife: -8.0476, -34.8770)',
     N'CC BY 4.0',
     0,
     N'Histórico de 7 dias + previsão de 1 dia. Dados modelados (ERA5 downscaled), não estação física. Limite: 10.000 req/dia sem token.'),

    (N'openmeteo_archive',
     N'Open-Meteo Archive ERA5',
     N'Open-Meteo GmbH / ECMWF',
     N'https://archive-api.open-meteo.com/v1/archive',
     N'horaria',
     N'Global (ponto Recife)',
     N'CC BY 4.0',
     0,
     N'Histórico longo via ERA5 reanalysis. Delay de ~5 dias. Janela coletada: 90 dias.'),

    (N'nasa_power',
     N'NASA POWER Reanalysis',
     N'NASA Langley Research Center',
     N'https://power.larc.nasa.gov/api/temporal/hourly/point',
     N'horaria',
     N'Global (ponto Recife)',
     N'Domínio público (NASA)',
     0,
     N'Reanálise MERRA-2. Delay de ~1 dia. Janela: 30 dias. Pressão em kPa (convertida para hPa × 10). Sentinela de dado ausente: -999.'),

    (N'dados_abertos_recife',
     N'Dados Abertos Recife — Arboviroses e Defesa Civil',
     N'Prefeitura do Recife / CKAN',
     N'https://dados.recife.pe.gov.br/api/3',
     N'semanal',
     N'Recife (bairro)',
     N'Open Data Commons ODbL 1.0',
     0,
     N'Portal CKAN do Recife. Arboviroses: notificações de dengue, zika e chikungunya. Defesa Civil: atendimentos mensais por tipo e bairro.'),

    (N'pysus_sinan',
     N'PySUS / SINAN ANIM',
     N'Ministério da Saúde / DATASUS',
     N'ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/',
     N'anual',
     N'Pernambuco (município)',
     N'Governo Federal (uso público)',
     0,
     N'Acesso via biblioteca PySUS (FTP DATASUS). Tenta o ano corrente; recua para o anterior se indisponível.'),

    (N'inmet',
     N'INMET — Estações Automáticas',
     N'Instituto Nacional de Meteorologia',
     N'https://apitempo.inmet.gov.br',
     N'horaria',
     N'Pernambuco (16 estações)',
     N'Governo Federal (uso público)',
     0,
     N'Metadados de estações coletados sem token. Observações horárias requerem token (portal.inmet.gov.br). Estação de referência: A301 (Recife/PE).');
GO
