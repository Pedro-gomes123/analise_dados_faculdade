import {
  BeforeUpdate,
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { decimalTransformer } from '@/infrastructure/database/transformers/decimal.transformer';

// RN-001. Never deleted, only deactivated (DEC-014).
@Entity({ name: 'parametro_alerta' })
export class ParametroAlerta {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  // Value of gold.leitura_climatica.variavel (DEC-009).
  @Column({ name: 'variavel', type: 'varchar', length: 50 })
  variavel!: string;

  // Territory identifier from the gold (DUV-009).
  @Column({ name: 'territorio', type: 'varchar', length: 50 })
  territorio!: string;

  @Column({
    name: 'limiar',
    type: 'decimal',
    precision: 12,
    scale: 3,
    transformer: decimalTransformer,
  })
  limiar!: number;

  // Level scale not documented yet (DUV-010): no enum until then.
  @Column({ name: 'nivel', type: 'varchar', length: 20 })
  nivel!: string;

  @Column({ name: 'ativo', type: 'bit', default: true })
  ativo!: boolean;

  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  // Same reason as Usuario: UTC (DEC-017), set on save().
  @Column({
    name: 'dthr_atualizacao',
    type: 'datetime2',
    precision: 3,
    default: () => 'SYSUTCDATETIME()',
  })
  dthrAtualizacao!: Date;

  @BeforeUpdate()
  tocarAtualizacao() {
    this.dthrAtualizacao = new Date();
  }
}
