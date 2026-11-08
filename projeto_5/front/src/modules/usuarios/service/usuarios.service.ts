import { http } from '@/lib/http'
import type { Paginated } from '@/lib/pagination'
import type {
  AlterarUsuarioRequest,
  CriarUsuarioRequest,
  ListarUsuariosParams,
  Usuario,
} from '@/modules/usuarios/types'

export const USUARIOS_POR_PAGINA = 20

export async function listarUsuarios({
  page,
  busca,
}: ListarUsuariosParams): Promise<Paginated<Usuario>> {
  const { data } = await http.get<Paginated<Usuario>>('/usuarios', {
    params: { page, limit: USUARIOS_POR_PAGINA, search: busca || undefined },
  })
  return data
}

export async function criarUsuario(dados: CriarUsuarioRequest): Promise<Usuario> {
  const { data } = await http.post<Usuario>('/usuarios', dados)
  return data
}

export async function alterarUsuario(id: number, dados: AlterarUsuarioRequest): Promise<Usuario> {
  const { data } = await http.patch<Usuario>(`/usuarios/${id}`, dados)
  return data
}
