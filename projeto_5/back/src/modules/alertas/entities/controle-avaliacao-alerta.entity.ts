import { BeforeUpdate, Column, Entity, PrimaryGeneratedColumn } from 'typeorm';

// Single row with the alert job marker (DEC-015). Created by the migration.
@Entity({ name: 'controle_avaliacao_alerta' })
export class ControleAvaliacaoAlerta {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  // Null means the job never ran. Only advances after the alerts are saved.
  @Column({
    name: 'ultima_lida_em',
    type: 'datetime2',
    precision: 3,
    nullable: true,
  })
  ultimaLidaEm!: Date | null;

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
