import {
  HttpStatus,
  NotFoundException,
  UnprocessableEntityException,
} from '@nestjs/common';
import type { DataSource, EntityManager, Repository } from 'typeorm';
import { BusinessRuleException } from '@/core/exceptions/business-rule.exception';
import { UsuarioPapel } from '@/modules/acesso/entities/usuario-papel.entity';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import type { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';
import {
  normalizarEmail,
  UsuarioService,
} from '@/modules/acesso/services/usuario.service';

function usuario(overrides: Partial<Usuario> = {}): Usuario {
  return Object.assign(new Usuario(), {
    id: 1,
    nome: 'Marcos Andrade',
    email: 'marcos@exemplo.gov.br',
    ativo: true,
    papeis: [],
    ...overrides,
  });
}

function setup() {
  const repo = {
    exists: jest.fn().mockResolvedValue(false),
    create: jest.fn((dados: Partial<Usuario>) =>
      Object.assign(new Usuario(), dados),
    ),
    save: jest.fn((u: Usuario) => Promise.resolve(Object.assign(u, { id: 1 }))),
    findOne: jest.fn().mockResolvedValue(usuario()),
  };
  const manager = {
    findOne: jest.fn().mockResolvedValue(usuario()),
    find: jest.fn().mockResolvedValue([]),
    remove: jest.fn().mockResolvedValue(undefined),
    insert: jest.fn().mockResolvedValue(undefined),
    save: jest.fn((_: unknown, u: Usuario) => Promise.resolve(u)),
  };
  const dataSource = {
    transaction: jest.fn((work: (m: EntityManager) => Promise<unknown>) =>
      work(manager as unknown as EntityManager),
    ),
  };
  const hasher = { hash: jest.fn().mockResolvedValue('hash-argon2') };

  const service = new UsuarioService(
    repo as unknown as Repository<Usuario>,
    dataSource as unknown as DataSource,
    hasher as unknown as PasswordHasher,
  );
  return { service, repo, manager, hasher };
}

const novo = {
  nome: '  Marcos Andrade ',
  email: ' Marcos@Exemplo.GOV.br ',
  senha: 'Senha-forte-1',
  papeis: [Papel.Tecnico, Papel.Tecnico],
};

describe('normalizarEmail', () => {
  it('trims and lowercases', () => {
    expect(normalizarEmail('  A@B.Com ')).toBe('a@b.com');
  });
});

describe('UsuarioService.criar (RN-010)', () => {
  it('creates an active user with normalized e-mail, hashed password and unique roles', async () => {
    const { service, repo, hasher } = setup();

    await service.criar(novo);

    expect(hasher.hash).toHaveBeenCalledWith('Senha-forte-1');
    expect(repo.create).toHaveBeenCalledWith({
      nome: 'Marcos Andrade',
      email: 'marcos@exemplo.gov.br',
      senhaHash: 'hash-argon2',
      ativo: true,
      papeis: [{ papel: Papel.Tecnico }],
    });
    expect(repo.findOne).toHaveBeenCalledWith({
      where: { id: 1 },
      relations: { papeis: true },
    });
  });

  it('rejects an e-mail that already exists, even inactive, with 409', async () => {
    const { service, repo } = setup();
    repo.exists.mockResolvedValue(true);

    const error = await service.criar(novo).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(BusinessRuleException);
    expect((error as BusinessRuleException).getStatus()).toBe(
      HttpStatus.CONFLICT,
    );
    expect((error as BusinessRuleException).businessRuleCode).toBe(
      'EMAIL_JA_CADASTRADO',
    );
    expect(repo.exists).toHaveBeenCalledWith({
      where: { email: 'marcos@exemplo.gov.br' },
    });
    expect(repo.save).not.toHaveBeenCalled();
  });

  it('turns a unique index violation (concurrent insert) into the same 409', async () => {
    const { service, repo } = setup();
    repo.save.mockRejectedValue({ driverError: { number: 2627 } });

    const error = await service.criar(novo).catch((e: unknown) => e);

    expect((error as BusinessRuleException).businessRuleCode).toBe(
      'EMAIL_JA_CADASTRADO',
    );
  });

  it('rethrows other database errors', async () => {
    const { service, repo } = setup();
    const failure = new Error('connection lost');
    repo.save.mockRejectedValue(failure);

    await expect(service.criar(novo)).rejects.toBe(failure);
  });

  it('rejects a user without roles with 422', async () => {
    const { service } = setup();

    await expect(service.criar({ ...novo, papeis: [] })).rejects.toBeInstanceOf(
      UnprocessableEntityException,
    );
  });
});

describe('UsuarioService.alterar', () => {
  it('replaces roles: removes the ones left out and inserts only the new ones', async () => {
    const { service, manager } = setup();
    const tec = Object.assign(new UsuarioPapel(), {
      id: 10,
      idUsuario: 1,
      papel: Papel.Tecnico,
    });
    const ges = Object.assign(new UsuarioPapel(), {
      id: 11,
      idUsuario: 1,
      papel: Papel.Gestor,
    });
    manager.find.mockResolvedValue([tec, ges]);

    await service.alterar(1, { papeis: [Papel.Gestor, Papel.Comunicacao] });

    expect(manager.remove).toHaveBeenCalledWith(UsuarioPapel, [tec]);
    expect(manager.insert).toHaveBeenCalledWith(UsuarioPapel, [
      { idUsuario: 1, papel: Papel.Comunicacao },
    ]);
  });

  it('deactivates instead of deleting (DEC-014) and touches dthr_atualizacao', async () => {
    const { service, manager } = setup();

    await service.alterar(1, { ativo: false });

    const [[entity, salvo]] = manager.save.mock.calls as [[unknown, Usuario]];
    expect(entity).toBe(Usuario);
    expect(salvo.ativo).toBe(false);
    expect(salvo.dthrAtualizacao).toBeInstanceOf(Date);
    expect(manager.remove).not.toHaveBeenCalled();
  });

  it('does not touch roles when they are not sent', async () => {
    const { service, manager } = setup();

    await service.alterar(1, { nome: 'Novo nome' });

    expect(manager.find).not.toHaveBeenCalled();
    expect(manager.insert).not.toHaveBeenCalled();
  });

  it('rejects an empty role list with 422', async () => {
    const { service } = setup();

    await expect(service.alterar(1, { papeis: [] })).rejects.toBeInstanceOf(
      UnprocessableEntityException,
    );
  });

  it('returns 404 for an unknown user', async () => {
    const { service, manager } = setup();
    manager.findOne.mockResolvedValue(null);

    await expect(service.alterar(99, { nome: 'x' })).rejects.toBeInstanceOf(
      NotFoundException,
    );
  });
});

describe('UsuarioService.buscarPorId', () => {
  it('returns 404 for an unknown user', async () => {
    const { service, repo } = setup();
    repo.findOne.mockResolvedValue(null);

    await expect(service.buscarPorId(99)).rejects.toBeInstanceOf(
      NotFoundException,
    );
  });
});
