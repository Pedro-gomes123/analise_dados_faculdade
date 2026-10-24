import { MigrationInterface, QueryRunner } from 'typeorm';

// erd.md: parametro_alerta, parametro_alerta_historico, alerta (MOD-002), acao
// (MOD-003) and controle_avaliacao_alerta (DEC-015). Schema `app` (DEC-016).
export class CriaTabelasAlertasAcoes1792900000001 implements MigrationInterface {
  name = 'CriaTabelasAlertasAcoes1792900000001';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TABLE [app].[parametro_alerta] (
        [id] int IDENTITY(1,1) NOT NULL,
        [variavel] varchar(50) NOT NULL,
        [territorio] varchar(50) NOT NULL,
        [limiar] decimal(12,3) NOT NULL,
        [nivel] varchar(20) NOT NULL,
        [ativo] bit NOT NULL CONSTRAINT [df_parametro_alerta_ativo] DEFAULT 1,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_parametro_alerta_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        [dthr_atualizacao] datetime2(3) NOT NULL CONSTRAINT [df_parametro_alerta_dthr_atualizacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_parametro_alerta] PRIMARY KEY ([id])
      )
    `);
    await queryRunner.query(
      `CREATE INDEX [idx_parametro_alerta_ativo_variavel_territorio] ON [app].[parametro_alerta] ([ativo], [variavel], [territorio])`,
    );

    await queryRunner.query(`
      CREATE TABLE [app].[parametro_alerta_historico] (
        [id] int IDENTITY(1,1) NOT NULL,
        [id_parametro_alerta] int NOT NULL,
        [id_usuario] int NOT NULL,
        [operacao] varchar(12) NOT NULL,
        [valor_anterior] nvarchar(max) NULL,
        [valor_novo] nvarchar(max) NOT NULL,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_parametro_alerta_historico_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_parametro_alerta_historico] PRIMARY KEY ([id]),
        CONSTRAINT [ck_parametro_alerta_historico_operacao] CHECK ([operacao] IN ('CRIACAO', 'ALTERACAO', 'INATIVACAO')),
        CONSTRAINT [fk_parametro_alerta_historico_parametro_alerta] FOREIGN KEY ([id_parametro_alerta])
          REFERENCES [app].[parametro_alerta] ([id]) ON DELETE NO ACTION,
        CONSTRAINT [fk_parametro_alerta_historico_usuario] FOREIGN KEY ([id_usuario])
          REFERENCES [app].[usuario] ([id]) ON DELETE NO ACTION
      )
    `);
    await queryRunner.query(
      `CREATE INDEX [idx_parametro_alerta_historico_parametro_dthr] ON [app].[parametro_alerta_historico] ([id_parametro_alerta], [dthr_criacao])`,
    );
    await queryRunner.query(
      `CREATE INDEX [idx_parametro_alerta_historico_id_usuario] ON [app].[parametro_alerta_historico] ([id_usuario])`,
    );

    await queryRunner.query(`
      CREATE TABLE [app].[alerta] (
        [id] int IDENTITY(1,1) NOT NULL,
        [id_parametro_alerta] int NOT NULL,
        [variavel] varchar(50) NOT NULL,
        [territorio] varchar(50) NOT NULL,
        [limiar] decimal(12,3) NOT NULL,
        [nivel] varchar(20) NOT NULL,
        [fonte] varchar(50) NOT NULL,
        [estacao] varchar(50) NOT NULL,
        [valor_lido] decimal(12,3) NOT NULL,
        [lida_em] datetime2(3) NOT NULL,
        [status] varchar(10) NOT NULL CONSTRAINT [df_alerta_status] DEFAULT 'ATIVO',
        [dthr_disparo] datetime2(3) NOT NULL CONSTRAINT [df_alerta_dthr_disparo] DEFAULT SYSUTCDATETIME(),
        [dthr_encerramento] datetime2(3) NULL,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_alerta_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        [dthr_atualizacao] datetime2(3) NOT NULL CONSTRAINT [df_alerta_dthr_atualizacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_alerta] PRIMARY KEY ([id]),
        CONSTRAINT [uq_alerta_parametro_leitura] UNIQUE ([id_parametro_alerta], [fonte], [estacao], [lida_em]),
        CONSTRAINT [ck_alerta_status] CHECK ([status] IN ('ATIVO', 'ENCERRADO')),
        CONSTRAINT [fk_alerta_parametro_alerta] FOREIGN KEY ([id_parametro_alerta])
          REFERENCES [app].[parametro_alerta] ([id]) ON DELETE NO ACTION
      )
    `);
    await queryRunner.query(
      `CREATE INDEX [idx_alerta_status_territorio] ON [app].[alerta] ([status], [territorio])`,
    );
    await queryRunner.query(
      `CREATE INDEX [idx_alerta_dthr_disparo] ON [app].[alerta] ([dthr_disparo])`,
    );

    await queryRunner.query(`
      CREATE TABLE [app].[acao] (
        [id] int IDENTITY(1,1) NOT NULL,
        [descricao] nvarchar(2000) NOT NULL,
        [id_alerta] int NULL,
        [id_usuario] int NOT NULL,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_acao_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_acao] PRIMARY KEY ([id]),
        CONSTRAINT [fk_acao_alerta] FOREIGN KEY ([id_alerta])
          REFERENCES [app].[alerta] ([id]) ON DELETE NO ACTION,
        CONSTRAINT [fk_acao_usuario] FOREIGN KEY ([id_usuario])
          REFERENCES [app].[usuario] ([id]) ON DELETE NO ACTION
      )
    `);
    await queryRunner.query(
      `CREATE INDEX [idx_acao_alerta_dthr_criacao] ON [app].[acao] ([id_alerta], [dthr_criacao])`,
    );
    await queryRunner.query(
      `CREATE INDEX [idx_acao_dthr_criacao] ON [app].[acao] ([dthr_criacao])`,
    );
    await queryRunner.query(
      `CREATE INDEX [idx_acao_id_usuario] ON [app].[acao] ([id_usuario])`,
    );

    await queryRunner.query(`
      CREATE TABLE [app].[controle_avaliacao_alerta] (
        [id] int IDENTITY(1,1) NOT NULL,
        [ultima_lida_em] datetime2(3) NULL,
        [dthr_atualizacao] datetime2(3) NOT NULL CONSTRAINT [df_controle_avaliacao_alerta_dthr_atualizacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_controle_avaliacao_alerta] PRIMARY KEY ([id])
      )
    `);
    // Single row; null marker means the job never ran (DEC-015).
    await queryRunner.query(
      `INSERT INTO [app].[controle_avaliacao_alerta] ([ultima_lida_em]) VALUES (NULL)`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE [app].[controle_avaliacao_alerta]`);
    await queryRunner.query(`DROP TABLE [app].[acao]`);
    await queryRunner.query(`DROP TABLE [app].[alerta]`);
    await queryRunner.query(`DROP TABLE [app].[parametro_alerta_historico]`);
    await queryRunner.query(`DROP TABLE [app].[parametro_alerta]`);
  }
}
