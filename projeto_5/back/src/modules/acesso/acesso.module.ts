import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { TypeOrmModule } from '@nestjs/typeorm';
import { EnvironmentVariables } from '@/core/config/env.validation';
import { AuthController } from '@/modules/acesso/controllers/auth.controller';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { AuthService } from '@/modules/acesso/services/auth.service';
import { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';
import { UsuarioService } from '@/modules/acesso/services/usuario.service';

@Module({
  imports: [
    TypeOrmModule.forFeature([Usuario, UsuarioPapel, RegistroAcesso]),
    JwtModule.registerAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService<EnvironmentVariables, true>) => ({
        secret: config.get('JWT_SECRET', { infer: true }),
        signOptions: {
          expiresIn: config.get('JWT_EXPIRES_IN', { infer: true }),
        },
      }),
    }),
  ],
  controllers: [AuthController],
  providers: [PasswordHasher, UsuarioService, AuthService],
  exports: [TypeOrmModule, JwtModule, PasswordHasher, UsuarioService],
})
export class AcessoModule {}
