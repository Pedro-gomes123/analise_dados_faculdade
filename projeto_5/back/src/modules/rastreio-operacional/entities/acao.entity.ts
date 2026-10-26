import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';

// RN-004: who, what and when. Insert-only, never edited (DEC-014).
@Entity({ name: 'acao' })
export class Acao {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  @Column({ name: 'descricao', type: 'nvarchar', length: 2000 })
  descricao!: string;

  // Optional link to the alert that motivated it (RN-004 #4, RN-006).
  @Column({ name: 'id_alerta', type: 'int', nullable: true })
  idAlerta!: number | null;

  @Column({ name: 'id_usuario', type: 'int' })
  idUsuario!: number;

  // Server time (RN-004), also the timeline order (RN-005).
  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  @ManyToOne(() => Alerta, { nullable: true })
  @JoinColumn({ name: 'id_alerta' })
  alerta!: Alerta | null;

  @ManyToOne(() => Usuario)
  @JoinColumn({ name: 'id_usuario' })
  usuario!: Usuario;
}
