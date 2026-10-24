import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';

@Module({
  imports: [TypeOrmModule.forFeature([Usuario, UsuarioPapel, RegistroAcesso])],
  providers: [PasswordHasher, UsuarioService],
  exports: [TypeOrmModule, PasswordHasher, UsuarioService],
})
export class AcessoModule {}
