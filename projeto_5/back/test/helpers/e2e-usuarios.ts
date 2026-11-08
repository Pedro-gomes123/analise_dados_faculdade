import request from 'supertest';
import { DataSource } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { Papel } from '@/modules/acesso/enums/papel.enum';
import { PasswordHasher } from '@/modules/acesso/services/password-hasher.service';
import type { AppE2e } from './e2e-app';

export const SENHA = 'senha-e2e-123';

let sequencia = 0;

interface DadosUsuario {
  nome?: string;
  email?: string;
  ativo?: boolean;
}

// Inserted straight in the database (state setup), with the real hasher.
export async function criarUsuario(
  app: AppE2e,
  papeis: Papel[],
  dados: DadosUsuario = {},
): Promise<Usuario> {
  sequencia += 1;
  const email =
    dados.email ?? `${papeis.join('-').toLowerCase()}-${sequencia}@e2e.gov.br`;
  const repositorio = app.get(DataSource).getRepository(Usuario);
  return repositorio.save(
    repositorio.create({
      nome: dados.nome ?? `Usuário ${sequencia}`,
      email,
      senhaHash: await app.get(PasswordHasher).hash(SENHA),
      ativo: dados.ativo ?? true,
      papeis: papeis.map((papel) => ({ papel })),
    }),
  );
}

export async function entrar(
  app: AppE2e,
  email: string,
  senha = SENHA,
): Promise<string> {
  const res = await request(app.getHttpServer())
    .post('/auth/login')
    .send({ email, senha })
    .expect(200);
  return (res.body as { access_token: string }).access_token;
}

// A logged-in user with the given roles.
export async function logado(app: AppE2e, papeis: Papel[]) {
  const usuario = await criarUsuario(app, papeis);
  return { usuario, token: await entrar(app, usuario.email) };
}
