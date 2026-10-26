// Entry point for `npm run seed:admin` (TASK-016). Never runs on app boot.
import dataSource from '@/infrastructure/database/data-source';
import {
  seedAdmin,
  validateSeedAdminEnv,
} from '@/modules/acesso/seed/seed-admin';
import { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';

async function main() {
  const env = validateSeedAdminEnv(process.env);
  await dataSource.initialize();
  try {
    const resultado = await seedAdmin(dataSource, new PasswordHasher(), env);
    console.log(
      resultado === 'criado'
        ? 'Administrador criado.'
        : 'Já existe um administrador; nada foi alterado.',
    );
  } finally {
    await dataSource.destroy();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
