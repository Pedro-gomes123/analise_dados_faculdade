import {
  BeforeUpdate,
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { decimalTransformer } from '@/infrastructure/database/transformers/decimal.transformer';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { StatusAlerta } from '@/modules/alertas/enums/status-alerta.enum';

// RN-002. Parameter fields are copied at trigger time, so the alert does not
// change if the parameter changes later. One alert per reading: RN-003.
@Entity({ name: 'alerta' })
export class Alerta {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  @Column({ name: 'id_parametro_alerta', type: 'int' })
  idParametroAlerta!: number;

  @Column({ name: 'variavel', type: 'varchar', length: 50 })
  variavel!: string;

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

  @Column({ name: 'nivel', type: 'varchar', length: 20 })
  nivel!: string;

  @Column({ name: 'fonte', type: 'varchar', length: 50 })
  fonte!: string;

  @Column({ name: 'estacao', type: 'varchar', length: 50 })
  estacao!: string;

  @Column({
    name: 'valor_lido',
    type: 'decimal',
    precision: 12,
    scale: 3,
    transformer: decimalTransformer,
  })
  valorLido!: number;

  @Column({ name: 'lida_em', type: 'datetime2', precision: 3 })
  lidaEm!: Date;

  @Column({
    name: 'status',
    type: 'varchar',
    length: 10,
    default: StatusAlerta.Ativo,
  })
  status!: StatusAlerta;

  // Start of the response time (RN-006).
  @Column({
    name: 'dthr_disparo',
    type: 'datetime2',
    precision: 3,
    default: () => 'SYSUTCDATETIME()',
  })
  dthrDisparo!: Date;

  @Column({
    name: 'dthr_encerramento',
    type: 'datetime2',
    precision: 3,
    nullable: true,
  })
  dthrEncerramento!: Date | null;

  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  @Column({
    name: 'dthr_atualizacao',
    type: 'datetime2',
    precision: 3,
    default: () => 'SYSUTCDATETIME()',
  })
  dthrAtualizacao!: Date;

  @ManyToOne(() => ParametroAlerta)
  @JoinColumn({ name: 'id_parametro_alerta' })
  parametroAlerta!: ParametroAlerta;

  @BeforeUpdate()
  tocarAtualizacao() {
    this.dthrAtualizacao = new Date();
  }
}
