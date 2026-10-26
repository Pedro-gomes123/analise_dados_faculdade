import type { DataSource, EntityManager } from 'typeorm';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import {
  seedAdmin,
  validateSeedAdminEnv,
} from '@/modules/acesso/seed/seed-admin';
import type { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';

const env = {
  ADMIN_NOME: '  Administrador ',
  ADMIN_EMAIL: 'Admin@Exemplo.gov.br',
  ADMIN_SENHA: 'senha-forte-1',
};

function setup({ admExiste = false, emailExiste = false } = {}) {
  const exists = jest.fn((entity: unknown) =>
    Promise.resolve(entity === UsuarioPapel ? admExiste : emailExiste),
  );
  const create = jest.fn((_: unknown, dados: Partial<Usuario>) =>
    Object.assign(new Usuario(), dados),
  );
  const save = jest.fn((_: unknown, u: Usuario) => Promise.resolve(u));
  const manager = { exists, create, save };
  const dataSource = {
    transaction: jest.fn((work: (m: EntityManager) => Promise<unknown>) =>
      work(manager as unknown as EntityManager),
    ),
  };
  const hash = jest.fn().mockResolvedValue('hash-argon2');
  const hasher = { hash } as unknown as PasswordHasher;

  return {
    run: () =>
      seedAdmin(
        dataSource as unknown as DataSource,
        hasher,
        validateSeedAdminEnv(env),
      ),
    exists,
    save,
    hash,
  };
}

describe('validateSeedAdminEnv', () => {
  it('aceita as três variáveis e apara o nome', () => {
    expect(validateSeedAdminEnv(env).ADMIN_NOME).toBe('Administrador');
  });

  it.each([
    ['ADMIN_EMAIL', 'nao-e-email'],
    ['ADMIN_SENHA', 'curta'],
    ['ADMIN_NOME', '   '],
  ])('recusa %s inválido', (chave, valor) => {
    expect(() => validateSeedAdminEnv({ ...env, [chave]: valor })).toThrow(
      'Invalid seed variables',
    );
  });

  it('recusa variável ausente', () => {
    expect(() =>
      validateSeedAdminEnv({ ADMIN_NOME: 'Adm', ADMIN_EMAIL: 'a@b.com' }),
    ).toThrow('Invalid seed variables');
  });
});

describe('seedAdmin', () => {
  it('cria o ADM ativo com e-mail normalizado e senha com hash', async () => {
    const { run, save, hash } = setup();

    await expect(run()).resolves.toBe('criado');

    expect(hash).toHaveBeenCalledWith('senha-forte-1');
    expect(save).toHaveBeenCalledWith(
      Usuario,
      expect.objectContaining({
        nome: 'Administrador',
        email: 'admin@exemplo.gov.br',
        senhaHash: 'hash-argon2',
        ativo: true,
        papeis: [{ papel: Papel.Administrador }],
      }),
    );
  });

  it('não cria nem altera nada quando já existe um ADM', async () => {
    const { run, save, hash } = setup({ admExiste: true });

    await expect(run()).resolves.toBe('ja-existe');

    expect(hash).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
  });

  it('não promove em silêncio um usuário existente sem papel ADM', async () => {
    const { run, save } = setup({ emailExiste: true });

    await expect(run()).rejects.toThrow(
      'já pertence a um usuário sem papel ADM',
    );
    expect(save).not.toHaveBeenCalled();
  });

  it('procura o e-mail já normalizado', async () => {
    const { run, exists } = setup();

    await run();

    expect(exists).toHaveBeenCalledWith(Usuario, {
      where: { email: 'admin@exemplo.gov.br' },
    });
  });
});
