IF SCHEMA_ID(N'silver') IS NULL EXEC(N'CREATE SCHEMA silver');
GO

IF OBJECT_ID(N'silver.INMET_Estacoes', N'U') IS NULL
BEGIN
    CREATE TABLE silver.INMET_Estacoes (
        [_id] NVARCHAR(64) NOT NULL CONSTRAINT PK_silver_INMET_Estacoes PRIMARY KEY,
        fonte NVARCHAR(255) NULL,
        tipo_dado NVARCHAR(255) NULL,
        municipio NVARCHAR(255) NULL,
        ingestao_ts DATETIMEOFFSET(6) NULL,
        codigo_distrito NVARCHAR(32) NULL,
        codigo_estacao NVARCHAR(32) NULL,
        codigo_oscar NVARCHAR(64) NULL,
        codigo_situacao NVARCHAR(64) NULL,
        codigo_wsi NVARCHAR(64) NULL,
        nome_estacao NVARCHAR(255) NULL,
        inicio_operacao DATETIMEOFFSET(6) NULL,
        fim_operacao DATETIMEOFFSET(6) NULL,
        flag_capital NVARCHAR(8) NULL,
        entidade NVARCHAR(64) NULL,
        estado NVARCHAR(8) NULL,
        tipo_estacao NVARCHAR(64) NULL,
        altitude DECIMAL(12, 3) NULL,
        latitude DECIMAL(12, 8) NULL,
        longitude DECIMAL(12, 8) NULL,
        payload_json NVARCHAR(MAX) NULL,
        documento_json NVARCHAR(MAX) NOT NULL,
        arquivo_hash BINARY(32) NOT NULL,
        blob_name NVARCHAR(1024) NOT NULL,
        linha_arquivo BIGINT NOT NULL,
        silver_carregado_em DATETIMEOFFSET(6) NOT NULL
            CONSTRAINT DF_silver_INMET_Estacoes_carregado DEFAULT (TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'))
    );
END;
GO

-- Evolução aditiva para tabelas piloto já existentes; não remove nem substitui dados.
IF COL_LENGTH(N'silver.INMET_Estacoes', N'codigo_distrito') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD codigo_distrito NVARCHAR(32) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'codigo_estacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD codigo_estacao NVARCHAR(32) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'codigo_oscar') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD codigo_oscar NVARCHAR(64) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'codigo_situacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD codigo_situacao NVARCHAR(64) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'codigo_wsi') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD codigo_wsi NVARCHAR(64) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'nome_estacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD nome_estacao NVARCHAR(255) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'inicio_operacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD inicio_operacao DATETIMEOFFSET(6) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'fim_operacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD fim_operacao DATETIMEOFFSET(6) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'flag_capital') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD flag_capital NVARCHAR(8) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'entidade') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD entidade NVARCHAR(64) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'estado') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD estado NVARCHAR(8) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'tipo_estacao') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD tipo_estacao NVARCHAR(64) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'altitude') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD altitude DECIMAL(12, 3) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'latitude') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD latitude DECIMAL(12, 8) NULL;
IF COL_LENGTH(N'silver.INMET_Estacoes', N'longitude') IS NULL
    ALTER TABLE silver.INMET_Estacoes ADD longitude DECIMAL(12, 8) NULL;
GO

IF OBJECT_ID(N'silver.Execucoes', N'U') IS NULL
BEGIN
    CREATE TABLE silver.Execucoes (
        execucao_id BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_silver_Execucoes PRIMARY KEY,
        procedure_name SYSNAME NOT NULL,
        iniciado_em DATETIMEOFFSET(6) NOT NULL,
        finalizado_em DATETIMEOFFSET(6) NOT NULL,
        registros_lidos BIGINT NOT NULL,
        registros_inseridos BIGINT NOT NULL,
        registros_rejeitados BIGINT NOT NULL,
        status NVARCHAR(20) NOT NULL,
        mensagem_erro NVARCHAR(4000) NULL
    );
END;
GO

CREATE OR ALTER PROCEDURE silver.sp_tratar_inmet
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @iniciado_em DATETIMEOFFSET(6) = TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00');
    DECLARE @lidos BIGINT = (SELECT COUNT_BIG(*) FROM staging.INMET_Estacoes);
    DECLARE @inseridos BIGINT = 0;
    DECLARE @rejeitados BIGINT = 0;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO staging.Rejeitados
            (file_hash, linha_arquivo, fonte, blob_name, [_id], documento_json, motivo, rejeitado_em)
        SELECT s.file_hash, s.linha_arquivo, N'INMET_Estacoes', s.blob_name,
               s.[_id], s.documento_json,
               CASE
                   WHEN s.[_id] IS NULL OR LTRIM(RTRIM(s.[_id])) = N'' THEN N'_id ausente'
                    WHEN ISNULL(ISJSON(s.documento_json), 0) <> 1 THEN N'documento_json não é JSON válido'
                    ELSE N'payload_json não é JSON válido'
               END,
               TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00')
        FROM staging.INMET_Estacoes AS s
        WHERE (s.[_id] IS NULL OR LTRIM(RTRIM(s.[_id])) = N''
               OR ISNULL(ISJSON(s.documento_json), 0) <> 1
               OR (s.payload_json IS NOT NULL AND ISNULL(ISJSON(s.payload_json), 0) <> 1))
          AND NOT EXISTS (
              SELECT 1 FROM staging.Rejeitados AS r
              WHERE r.file_hash = s.file_hash
                AND r.linha_arquivo = s.linha_arquivo
                AND r.fonte = N'INMET_Estacoes'
          );
        SET @rejeitados = @@ROWCOUNT;

        ;WITH validos AS (
            SELECT s.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY s.[_id]
                       ORDER BY s.ingestao_ts DESC, s.file_hash DESC, s.linha_arquivo DESC
                   ) AS rn
            FROM staging.INMET_Estacoes AS s
            WHERE s.[_id] IS NOT NULL
              AND LTRIM(RTRIM(s.[_id])) <> N''
              AND ISNULL(ISJSON(s.documento_json), 0) = 1
              AND (s.payload_json IS NULL OR ISJSON(s.payload_json) = 1)
        )
        SELECT v.[_id], v.fonte, v.tipo_dado, v.municipio, v.ingestao_ts,
               v.payload_json, v.documento_json, v.file_hash, v.blob_name, v.linha_arquivo,
               JSON_VALUE(v.payload_json, '$.CD_DISTRITO') AS codigo_distrito,
               JSON_VALUE(v.payload_json, '$.CD_ESTACAO') AS codigo_estacao,
               JSON_VALUE(v.payload_json, '$.CD_OSCAR') AS codigo_oscar,
               JSON_VALUE(v.payload_json, '$.CD_SITUACAO') AS codigo_situacao,
               JSON_VALUE(v.payload_json, '$.CD_WSI') AS codigo_wsi,
               JSON_VALUE(v.payload_json, '$.DC_NOME') AS nome_estacao,
               TRY_CONVERT(datetimeoffset(6), JSON_VALUE(v.payload_json, '$.DT_INICIO_OPERACAO')) AS inicio_operacao,
               TRY_CONVERT(datetimeoffset(6), JSON_VALUE(v.payload_json, '$.DT_FIM_OPERACAO')) AS fim_operacao,
               JSON_VALUE(v.payload_json, '$.FL_CAPITAL') AS flag_capital,
               JSON_VALUE(v.payload_json, '$.SG_ENTIDADE') AS entidade,
               JSON_VALUE(v.payload_json, '$.SG_ESTADO') AS estado,
               JSON_VALUE(v.payload_json, '$.TP_ESTACAO') AS tipo_estacao,
               TRY_CONVERT(decimal(12, 3), JSON_VALUE(v.payload_json, '$.VL_ALTITUDE')) AS altitude,
               TRY_CONVERT(decimal(12, 8), JSON_VALUE(v.payload_json, '$.VL_LATITUDE')) AS latitude,
               TRY_CONVERT(decimal(12, 8), JSON_VALUE(v.payload_json, '$.VL_LONGITUDE')) AS longitude
        INTO #validos
        FROM validos AS v
        WHERE v.rn = 1;

        UPDATE t
        SET t.fonte = v.fonte,
            t.tipo_dado = v.tipo_dado,
            t.municipio = v.municipio,
            t.ingestao_ts = v.ingestao_ts,
            t.codigo_distrito = v.codigo_distrito,
            t.codigo_estacao = v.codigo_estacao,
            t.codigo_oscar = v.codigo_oscar,
            t.codigo_situacao = v.codigo_situacao,
            t.codigo_wsi = v.codigo_wsi,
            t.nome_estacao = v.nome_estacao,
            t.inicio_operacao = v.inicio_operacao,
            t.fim_operacao = v.fim_operacao,
            t.flag_capital = v.flag_capital,
            t.entidade = v.entidade,
            t.estado = v.estado,
            t.tipo_estacao = v.tipo_estacao,
            t.altitude = v.altitude,
            t.latitude = v.latitude,
            t.longitude = v.longitude,
            t.payload_json = v.payload_json,
            t.documento_json = v.documento_json,
            t.arquivo_hash = v.file_hash,
            t.blob_name = v.blob_name,
            t.linha_arquivo = v.linha_arquivo,
            t.silver_carregado_em = TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00')
        FROM silver.INMET_Estacoes AS t
        INNER JOIN #validos AS v ON v.[_id] = t.[_id];

        INSERT INTO silver.INMET_Estacoes
            ([_id], fonte, tipo_dado, municipio, ingestao_ts,
             codigo_distrito, codigo_estacao, codigo_oscar, codigo_situacao, codigo_wsi,
             nome_estacao, inicio_operacao, fim_operacao, flag_capital, entidade,
             estado, tipo_estacao, altitude, latitude, longitude, payload_json,
             documento_json, arquivo_hash, blob_name, linha_arquivo)
        SELECT v.[_id], v.fonte, v.tipo_dado, v.municipio, v.ingestao_ts,
               v.codigo_distrito, v.codigo_estacao, v.codigo_oscar, v.codigo_situacao,
               v.codigo_wsi, v.nome_estacao, v.inicio_operacao, v.fim_operacao,
               v.flag_capital, v.entidade, v.estado, v.tipo_estacao, v.altitude,
               v.latitude, v.longitude, v.payload_json, v.documento_json,
               v.file_hash, v.blob_name, v.linha_arquivo
        FROM #validos AS v
        WHERE NOT EXISTS (
            SELECT 1 FROM silver.INMET_Estacoes AS t WITH (UPDLOCK, HOLDLOCK)
            WHERE t.[_id] = v.[_id]
        );
        SET @inseridos = @@ROWCOUNT;

        INSERT INTO silver.Execucoes
            (procedure_name, iniciado_em, finalizado_em, registros_lidos,
             registros_inseridos, registros_rejeitados, status, mensagem_erro)
        VALUES
            (N'silver.sp_tratar_inmet', @iniciado_em,
             TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'), @lidos,
             @inseridos, @rejeitados, N'concluido', NULL);

        COMMIT TRANSACTION;
        SELECT @lidos AS registros_lidos,
               @inseridos AS registros_inseridos,
               @rejeitados AS registros_rejeitados,
               N'concluido' AS status;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;

        INSERT INTO silver.Execucoes
            (procedure_name, iniciado_em, finalizado_em, registros_lidos,
             registros_inseridos, registros_rejeitados, status, mensagem_erro)
        VALUES
            (N'silver.sp_tratar_inmet', @iniciado_em,
             TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00'), @lidos,
             @inseridos, @rejeitados, N'erro', ERROR_MESSAGE());

        THROW;
    END CATCH;
END;
GO
