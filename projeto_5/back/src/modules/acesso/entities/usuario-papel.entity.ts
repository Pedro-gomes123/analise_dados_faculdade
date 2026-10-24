import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';

@Entity({ name: 'usuario_papel' })
export class UsuarioPapel {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  @Column({ name: 'id_usuario', type: 'int' })
  idUsuario!: number;

  @Column({ name: 'papel', type: 'varchar', length: 3 })
  papel!: Papel;

  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  @ManyToOne(() => Usuario, (usuario) => usuario.papeis)
  @JoinColumn({ name: 'id_usuario' })
  usuario!: Usuario;
}
