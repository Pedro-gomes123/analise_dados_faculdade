IF SCHEMA_ID(N'staging') IS NULL EXEC(N'CREATE SCHEMA staging');
GO

IF OBJECT_ID(N'staging.ArquivosProcessados', N'U') IS NULL
BEGIN
    CREATE TABLE staging.ArquivosProcessados (
        file_hash BINARY(32) NOT NULL CONSTRAINT PK_staging_ArquivosProcessados PRIMARY KEY,
        blob_name NVARCHAR(1024) NOT NULL,
        fonte NVARCHAR(100) NOT NULL,
        processado_em DATETIMEOFFSET(6) NOT NULL,
        registros_lidos BIGINT NOT NULL CONSTRAINT DF_staging_Arquivos_lidos DEFAULT (0),
        registros_inseridos BIGINT NOT NULL CONSTRAINT DF_staging_Arquivos_inseridos DEFAULT (0),
        status NVARCHAR(20) NOT NULL,
        mensagem_erro NVARCHAR(4000) NULL
    );
END;
GO

IF OBJECT_ID(N'staging.INMET_Estacoes', N'U') IS NULL
BEGIN
    CREATE TABLE staging.INMET_Estacoes (
        file_hash BINARY(32) NOT NULL,
        linha_arquivo BIGINT NOT NULL,
        blob_name NVARCHAR(1024) NOT NULL,
        [_id] NVARCHAR(64) NULL,
        fonte NVARCHAR(255) NULL,
        tipo_dado NVARCHAR(255) NULL,
        municipio NVARCHAR(255) NULL,
        ingestao_ts DATETIMEOFFSET(6) NULL,
        payload_json NVARCHAR(MAX) NULL,
        documento_json NVARCHAR(MAX) NULL,
        CONSTRAINT PK_staging_INMET_Estacoes PRIMARY KEY (file_hash, linha_arquivo)
    );
    CREATE INDEX IX_staging_INMET_Estacoes_id ON staging.INMET_Estacoes ([_id]);
END;
GO

IF OBJECT_ID(N'staging.Rejeitados', N'U') IS NULL
BEGIN
    CREATE TABLE staging.Rejeitados (
        file_hash BINARY(32) NOT NULL,
        linha_arquivo BIGINT NOT NULL,
        fonte NVARCHAR(100) NOT NULL,
        blob_name NVARCHAR(1024) NOT NULL,
        [_id] NVARCHAR(64) NULL,
        documento_json NVARCHAR(MAX) NULL,
        motivo NVARCHAR(1000) NOT NULL,
        rejeitado_em DATETIMEOFFSET(6) NOT NULL,
        CONSTRAINT PK_staging_Rejeitados PRIMARY KEY (file_hash, linha_arquivo, fonte)
    );
END;
GO
