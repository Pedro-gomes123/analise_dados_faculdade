import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Paginated } from '@/lib/pagination'
import { UsuariosPage } from '@/modules/usuarios/components/UsuariosPage'
import { alterarUsuario, listarUsuarios } from '@/modules/usuarios/service/usuarios.service'
import type { Usuario } from '@/modules/usuarios/types'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/usuarios/service/usuarios.service', () => ({
  listarUsuarios: vi.fn(),
  criarUsuario: vi.fn(),
  alterarUsuario: vi.fn(),
}))

const listarMock = vi.mocked(listarUsuarios)
const alterarMock = vi.mocked(alterarUsuario)

const usuarios: Usuario[] = [
  { id: 1, nome: 'Ana Lima', email: 'ana@x.gov.br', papeis: ['ADM'], ativo: true },
  { id: 2, nome: 'Bruno Costa', email: 'bruno@x.gov.br', papeis: ['GES', 'TEC'], ativo: false },
]

function pagina(data: Usuario[], totalPages = 1): Paginated<Usuario> {
  return {
    data,
    meta: { itemsPerPage: 20, totalItems: data.length, currentPage: 1, totalPages },
  }
}

function setup(page = 1, busca = '') {
  const onSearchChange = vi.fn()
  renderWithQuery(<UsuariosPage page={page} busca={busca} onSearchChange={onSearchChange} />)
  return { onSearchChange }
}

describe('UsuariosPage', () => {
  beforeEach(() => {
    listarMock.mockReset()
    alterarMock.mockReset()
  })

  it('lista os usuários com papéis e situação', async () => {
    listarMock.mockResolvedValue(pagina(usuarios))
    setup()

    const linha = (await screen.findByText('Bruno Costa')).closest('tr')!
    expect(within(linha).getByText('GES')).toBeInTheDocument()
    expect(within(linha).getByText('Inativo')).toBeInTheDocument()
    expect(within(linha).getByRole('button', { name: 'Reativar' })).toBeInTheDocument()
    expect(listarMock).toHaveBeenCalledWith({ page: 1, busca: '' })
  })

  it('busca voltando para a primeira página', async () => {
    listarMock.mockResolvedValue(pagina(usuarios, 3))
    const { onSearchChange } = setup(2)

    await userEvent.type(screen.getByLabelText('Buscar por nome ou e-mail'), ' ana ')
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }))

    expect(onSearchChange).toHaveBeenCalledWith({ page: 1, busca: 'ana' })
  })

  it('inativa só depois de confirmar (DEC-014)', async () => {
    listarMock.mockResolvedValue(pagina(usuarios))
    alterarMock.mockResolvedValue({ ...usuarios[0]!, ativo: false })
    setup()

    const linha = (await screen.findByText('Ana Lima')).closest('tr')!
    await userEvent.click(within(linha).getByRole('button', { name: 'Inativar' }))
    expect(alterarMock).not.toHaveBeenCalled()

    const dialogo = await screen.findByRole('dialog')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Inativar' }))

    expect(alterarMock).toHaveBeenCalledWith(1, { ativo: false })
  })

  it('mostra aviso quando a lista está vazia', async () => {
    listarMock.mockResolvedValue(pagina([]))
    setup()

    expect(await screen.findByText('Nenhum usuário encontrado.')).toBeInTheDocument()
  })
})
