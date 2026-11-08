import { plainToInstance, Transform } from 'class-transformer';
import {
  IsEmail,
  IsNotEmpty,
  IsString,
  MaxLength,
  MinLength,
  validateSync,
} from 'class-validator';
import type { DataSource } from 'typeorm';
import { SENHA_MIN } from '@/modules/acesso/dto/criar-usuario.dto';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import type { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';
import { normalizarEmail } from '@/modules/acesso/services/usuario.service';

const trim = ({ value }: { value: unknown }) =>
  typeof value === 'string' ? value.trim() : value;

// TASK-016. Same limits as CriarUsuarioDto (RN-010, PR-020).
export class SeedAdminEnv {
  @Transform(trim)
  @IsString()
  @IsNotEmpty()
  @MaxLength(150)
  ADMIN_NOME!: string;

  @IsEmail()
  @MaxLength(254)
  ADMIN_EMAIL!: string;

  @IsString()
  @MinLength(SENHA_MIN)
  @MaxLength(128)
  ADMIN_SENHA!: string;
}

export function validateSeedAdminEnv(config: Record<string, unknown>) {
  const validated = plainToInstance(SeedAdminEnv, config);
  const errors = validateSync(validated);

  if (errors.length > 0) {
    const messages = errors.flatMap((error) =>
      Object.values(error.constraints ?? {}),
    );
    throw new Error(`Invalid seed variables:\n${messages.join('\n')}`);
  }

  return validated;
}

export type SeedAdminResultado = 'criado' | 'ja-existe';

// Idempotent: once any ADM exists, nothing is created or changed (the password
// is never overwritten). An existing non-ADM account with the same e-mail is
// not promoted silently.
export async function seedAdmin(
  dataSource: DataSource,
  hasher: PasswordHasher,
  env: SeedAdminEnv,
): Promise<SeedAdminResultado> {
  return dataSource.transaction(async (manager) => {
    if (
      await manager.exists(UsuarioPapel, {
        where: { papel: Papel.Administrador },
      })
    ) {
      return 'ja-existe';
    }

    const email = normalizarEmail(env.ADMIN_EMAIL);
    if (await manager.exists(Usuario, { where: { email } })) {
      throw new Error(
        `E-mail ${email} já pertence a um usuário sem papel ADM; use outro ADMIN_EMAIL`,
      );
    }

    const usuario = manager.create(Usuario, {
      nome: env.ADMIN_NOME,
      email,
      senhaHash: await hasher.hash(env.ADMIN_SENHA),
      ativo: true,
      papeis: [{ papel: Papel.Administrador }],
    });
    await manager.save(Usuario, usuario);
    return 'criado';
  });
}
