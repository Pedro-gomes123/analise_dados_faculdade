import { UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import type { Repository } from 'typeorm';
import { RegistroAcesso } from '@/modules/acesso/entities/registro-acesso.entity';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import {
  AuthService,
  JwtPayload,
  LOGIN_INVALIDO_MESSAGE,
} from '@/modules/acesso/services/auth.service';
import type { UsuarioService } from '@/modules/acesso/services/usuario.service';

const SECRET = 'x'.repeat(32);

function usuario(overrides: Partial<Usuario> = {}): Usuario {
  return Object.assign(new Usuario(), {
    id: 7,
    nome: 'Camila Rocha',
    email: 'camila@exemplo.gov.br',
    senhaHash: 'hash-real',
    ativo: true,
    papeis: [
      Object.assign(new UsuarioPapel(), { papel: Papel.Gestor }),
      Object.assign(new UsuarioPapel(), { papel: Papel.GestaoInstitucional }),
    ],
    ...overrides,
  });
}

function setup(found: Usuario | null, senhaConfere: boolean) {
  const usuarios = { buscarParaLogin: jest.fn().mockResolvedValue(found) };
  const hasher = {
    verify: jest.fn().mockResolvedValue(senhaConfere),
    hash: jest.fn().mockResolvedValue('hash-ficticio'),
  };
  const registros = { insert: jest.fn().mockResolvedValue(undefined) };
  const jwt = new JwtService({
    secret: SECRET,
    signOptions: { expiresIn: '8h' },
  });

  const service = new AuthService(
    usuarios as unknown as UsuarioService,
    hasher,
    jwt,
    registros as unknown as Repository<RegistroAcesso>,
  );
  return { service, hasher, registros, jwt };
}

async function falha(promise: Promise<unknown>) {
  const error = await promise.catch((e: unknown) => e);
  expect(error).toBeInstanceOf(UnauthorizedException);
  expect((error as UnauthorizedException).message).toBe(LOGIN_INVALIDO_MESSAGE);
}

describe('AuthService.login (FLX-001)', () => {
  it('returns a JWT with the user id and the user without the password hash', async () => {
    const { service, jwt } = setup(usuario(), true);

    const result = await service.login('camila@exemplo.gov.br', 'Senha-1');

    const payload = await jwt.verifyAsync<JwtPayload>(result.access_token);
    expect(payload.sub).toBe(7);
    expect(result.usuario).toEqual({
      id: 7,
      nome: 'Camila Rocha',
      email: 'camila@exemplo.gov.br',
      papeis: [Papel.Gestor, Papel.GestaoInstitucional].sort(),
      ativo: true,
    });
    expect(JSON.stringify(result)).not.toContain('hash-real');
  });

  it('records a successful login (RN-011)', async () => {
    const { service, registros } = setup(usuario(), true);

    await service.login(' camila@exemplo.gov.br ', 'Senha-1');

    expect(registros.insert).toHaveBeenCalledWith({
      emailInformado: 'camila@exemplo.gov.br',
      idUsuario: 7,
      sucesso: true,
    });
  });

  it('rejects a wrong password with 401 and records the failure', async () => {
    const { service, registros } = setup(usuario(), false);

    await falha(service.login('camila@exemplo.gov.br', 'errada'));

    expect(registros.insert).toHaveBeenCalledWith({
      emailInformado: 'camila@exemplo.gov.br',
      idUsuario: 7,
      sucesso: false,
    });
  });

  it('rejects an unknown e-mail with the same message, still checking a password', async () => {
    const { service, registros, hasher } = setup(null, true);

    await falha(service.login('ninguem@exemplo.gov.br', 'qualquer'));

    expect(hasher.verify).toHaveBeenCalledWith('hash-ficticio', 'qualquer');
    expect(registros.insert).toHaveBeenCalledWith({
      emailInformado: 'ninguem@exemplo.gov.br',
      idUsuario: null,
      sucesso: false,
    });
  });

  it('rejects an inactive user even with the right password (RN-010 #5)', async () => {
    const { service, registros } = setup(usuario({ ativo: false }), true);

    await falha(service.login('camila@exemplo.gov.br', 'Senha-1'));

    expect(registros.insert).toHaveBeenCalledWith(
      expect.objectContaining({ sucesso: false }),
    );
  });

  it('never records the password', async () => {
    const { service, registros } = setup(usuario(), false);

    await service
      .login('camila@exemplo.gov.br', 'segredo-123')
      .catch(() => undefined);

    expect(JSON.stringify(registros.insert.mock.calls)).not.toContain(
      'segredo-123',
    );
  });
});
