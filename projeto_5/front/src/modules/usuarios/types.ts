import type { Papel } from '@/modules/auth/types'

export type { Usuario } from '@/modules/auth/types'

export interface CriarUsuarioRequest {
  nome: string
  email: string
  senha: string
  papeis: Papel[]
}

// E-mail não é editável (RN-010). Senha só quando o ADM redefine (PR-020).
export interface AlterarUsuarioRequest {
  nome?: string
  senha?: string
  papeis?: Papel[]
  ativo?: boolean
}

export interface ListarUsuariosParams {
  page: number
  busca?: string
}
