import { MigrationInterface, QueryRunner } from 'typeorm';

// erd.md: usuario, usuario_papel, registro_acesso (MOD-001). Schema `app` (DEC-016).
export class CriaTabelasAcesso1792900000000 implements MigrationInterface {
  name = 'CriaTabelasAcesso1792900000000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TABLE [app].[usuario] (
        [id] int IDENTITY(1,1) NOT NULL,
        [nome] nvarchar(150) NOT NULL,
        [email] nvarchar(254) NOT NULL,
        [senha_hash] nvarchar(255) NOT NULL,
        [ativo] bit NOT NULL CONSTRAINT [df_usuario_ativo] DEFAULT 1,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_usuario_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        [dthr_atualizacao] datetime2(3) NOT NULL CONSTRAINT [df_usuario_dthr_atualizacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_usuario] PRIMARY KEY ([id]),
        CONSTRAINT [uq_usuario_email] UNIQUE ([email])
      )
    `);

    await queryRunner.query(`
      CREATE TABLE [app].[usuario_papel] (
        [id] int IDENTITY(1,1) NOT NULL,
        [id_usuario] int NOT NULL,
        [papel] varchar(3) NOT NULL,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_usuario_papel_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_usuario_papel] PRIMARY KEY ([id]),
        CONSTRAINT [uq_usuario_papel_usuario_papel] UNIQUE ([id_usuario], [papel]),
        CONSTRAINT [ck_usuario_papel_papel] CHECK ([papel] IN ('TEC', 'GES', 'GIN', 'COM', 'ADM')),
        CONSTRAINT [fk_usuario_papel_usuario] FOREIGN KEY ([id_usuario])
          REFERENCES [app].[usuario] ([id]) ON DELETE NO ACTION
      )
    `);

    await queryRunner.query(`
      CREATE TABLE [app].[registro_acesso] (
        [id] int IDENTITY(1,1) NOT NULL,
        [email_informado] nvarchar(254) NOT NULL,
        [id_usuario] int NULL,
        [sucesso] bit NOT NULL,
        [dthr_criacao] datetime2(3) NOT NULL CONSTRAINT [df_registro_acesso_dthr_criacao] DEFAULT SYSUTCDATETIME(),
        CONSTRAINT [pk_registro_acesso] PRIMARY KEY ([id]),
        CONSTRAINT [fk_registro_acesso_usuario] FOREIGN KEY ([id_usuario])
          REFERENCES [app].[usuario] ([id]) ON DELETE NO ACTION
      )
    `);
    await queryRunner.query(
      `CREATE INDEX [idx_registro_acesso_dthr_criacao] ON [app].[registro_acesso] ([dthr_criacao])`,
    );
    await queryRunner.query(
      `CREATE INDEX [idx_registro_acesso_id_usuario] ON [app].[registro_acesso] ([id_usuario])`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE [app].[registro_acesso]`);
    await queryRunner.query(`DROP TABLE [app].[usuario_papel]`);
    await queryRunner.query(`DROP TABLE [app].[usuario]`);
  }
}
