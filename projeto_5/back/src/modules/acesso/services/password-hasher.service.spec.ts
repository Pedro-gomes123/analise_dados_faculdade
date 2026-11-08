import { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';

describe('PasswordHasher', () => {
  const hasher = new PasswordHasher();

  it('hashes with argon2id and never returns the plain password', async () => {
    const hash = await hasher.hash('Senha-forte-1');

    expect(hash.startsWith('$argon2id$')).toBe(true);
    expect(hash).not.toContain('Senha-forte-1');
  });

  it('verifies the right password and rejects a wrong one', async () => {
    const hash = await hasher.hash('Senha-forte-1');

    await expect(hasher.verify(hash, 'Senha-forte-1')).resolves.toBe(true);
    await expect(hasher.verify(hash, 'outra')).resolves.toBe(false);
  });
});
