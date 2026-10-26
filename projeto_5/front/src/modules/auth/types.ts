// Papéis de permissoes.md (PER-001 a PER-013). O back devolve em ordem alfabética.
export type Papel = 'TEC' | 'GES' | 'GIN' | 'COM' | 'ADM'

export interface Usuario {
  id: number
  nome: string
  email: string
  papeis: Papel[]
  ativo: boolean
}

export interface LoginRequest {
  email: string
  senha: string
}

export interface LoginResponse {
  access_token: string
  usuario: Usuario
}
