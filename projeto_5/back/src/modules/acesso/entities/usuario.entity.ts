import {
  BeforeUpdate,
  Column,
  CreateDateColumn,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';

@Entity({ name: 'usuario' })
export class Usuario {
  @PrimaryGeneratedColumn({ name: 'id' })
  id!: number;

  @Column({ name: 'nome', type: 'nvarchar', length: 150 })
  nome!: string;

  @Column({ name: 'email', type: 'nvarchar', length: 254 })
  email!: string;

  // Never returned by default queries (DEC-013).
  @Column({ name: 'senha_hash', type: 'nvarchar', length: 255, select: false })
  senhaHash!: string;

  @Column({ name: 'ativo', type: 'bit', default: true })
  ativo!: boolean;

  @CreateDateColumn({ name: 'dthr_criacao', type: 'datetime2', precision: 3 })
  dthrCriacao!: Date;

  // Not @UpdateDateColumn: TypeORM would write getdate() (server local time),
  // and DEC-017 stores UTC. Updates must go through save().
  @Column({
    name: 'dthr_atualizacao',
    type: 'datetime2',
    precision: 3,
    default: () => 'SYSUTCDATETIME()',
  })
  dthrAtualizacao!: Date;

  @OneToMany(() => UsuarioPapel, (papel) => papel.usuario, {
    cascade: ['insert'],
  })
  papeis!: UsuarioPapel[];

  @BeforeUpdate()
  tocarAtualizacao() {
    this.dthrAtualizacao = new Date();
  }
}
