import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Usuario, UsuarioPapel, RegistroAcesso])],
  exports: [TypeOrmModule],
})
export class AcessoModule {}
