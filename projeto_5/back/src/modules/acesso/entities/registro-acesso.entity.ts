import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';

// Insert-only login log (RN-011, DEC-014). The password is never stored here.
@Entity({ name: 'registro_acesso' })
export class RegistroAcesso {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  @Column({ name: 'email_informado', type: 'nvarchar', length: 254 })
  emailInformado!: string;

  @Column({ name: 'id_usuario', type: 'int', nullable: true })
  idUsuario!: number | null;

  @Column({ name: 'sucesso', type: 'bit' })
  sucesso!: boolean;

  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  @ManyToOne(() => Usuario, { nullable: true })
  @JoinColumn({ name: 'id_usuario' })
  usuario!: Usuario | null;
}
