import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UsuarioFormDialog } from '@/modules/usuarios/components/UsuarioFormDialog'
import { alterarUsuario, criarUsuario } from '@/modules/usuarios/service/usuarios.service'
import type { Usuario } from '@/modules/usuarios/types'
import { apiError } from '@/test/api-error'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/usuarios/service/usuarios.service', () => ({
  listarUsuarios: vi.fn(),
  criarUsuario: vi.fn(),
  alterarUsuario: vi.fn(),
}))

const criarMock = vi.mocked(criarUsuario)
const alterarMock = vi.mocked(alterarUsuario)

const marcos: Usuario = {
  id: 7,
  nome: 'Marcos Andrade',
  email: 'marcos@exemplo.gov.br',
  papeis: ['GES'],
  ativo: true,
}

function setup(usuario?: Usuario) {
  const onOpenChange = vi.fn()
  renderWithQuery(<UsuarioFormDialog open onOpenChange={onOpenChange} usuario={usuario} />)
  return { onOpenChange }
}

const salvar = () => screen.getByRole('button', { name: 'Salvar' })

describe('UsuarioFormDialog: cadastro', () => {
  beforeEach(() => {
    criarMock.mockReset()
    alterarMock.mockReset()
  })

  it('só habilita salvar com nome, e-mail, senha válida e ao menos um papel (RN-010)', async () => {
    setup()
    await userEvent.type(screen.getByLabelText('Nome'), 'Ana')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.gov.br')
    await userEvent.type(screen.getByLabelText('Senha inicial'), 'curta')

    expect(screen.getByText('A senha precisa ter ao menos 8 caracteres')).toBeInTheDocument()
    expect(salvar()).toBeDisabled()

    await userEvent.type(screen.getByLabelText('Senha inicial'), '-agora-longa')
    expect(salvar()).toBeDisabled()

    await userEvent.click(screen.getByLabelText('Técnico(a) Vigidesastres'))
    expect(salvar()).toBeEnabled()
  })

  it('cria o usuário com os papéis na ordem das estações e fecha', async () => {
    criarMock.mockResolvedValue({ ...marcos, id: 8 })
    const { onOpenChange } = setup()

    await userEvent.type(screen.getByLabelText('Nome'), ' Ana ')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.gov.br')
    await userEvent.type(screen.getByLabelText('Senha inicial'), 'senha-forte-1')
    await userEvent.click(screen.getByLabelText('Comunicação Institucional'))
    await userEvent.click(screen.getByLabelText('Técnico(a) Vigidesastres'))
    await userEvent.click(salvar())

    expect(criarMock.mock.calls[0]?.[0]).toEqual({
      nome: 'Ana',
      email: 'ana@exemplo.gov.br',
      senha: 'senha-forte-1',
      papeis: ['TEC', 'COM'],
    })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('mostra o 409 de e-mail já cadastrado e mantém aberto', async () => {
    criarMock.mockRejectedValue(
      apiError(409, {
        message: 'Já existe um usuário com este e-mail',
        business_rule_code: 'EMAIL_JA_CADASTRADO',
      }),
    )
    const { onOpenChange } = setup()

    await userEvent.type(screen.getByLabelText('Nome'), 'Ana')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ana@exemplo.gov.br')
    await userEvent.type(screen.getByLabelText('Senha inicial'), 'senha-forte-1')
    await userEvent.click(screen.getByLabelText('Administrador'))
    await userEvent.click(salvar())

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Já existe um usuário com este e-mail',
    )
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})

describe('UsuarioFormDialog: edição', () => {
  beforeEach(() => {
    alterarMock.mockReset()
  })

  it('não deixa trocar o e-mail (RN-010)', () => {
    setup(marcos)
    expect(screen.getByLabelText('E-mail')).toBeDisabled()
  })

  it('não envia senha quando o campo fica em branco', async () => {
    alterarMock.mockResolvedValue(marcos)
    setup(marcos)

    await userEvent.click(screen.getByLabelText('Técnico(a) Vigidesastres'))
    await userEvent.click(salvar())

    expect(alterarMock).toHaveBeenCalledWith(7, { nome: 'Marcos Andrade', papeis: ['TEC', 'GES'] })
  })

  it('redefine a senha quando o ADM preenche (PR-020)', async () => {
    alterarMock.mockResolvedValue(marcos)
    setup(marcos)

    await userEvent.type(
      screen.getByLabelText('Nova senha (deixe em branco para manter)'),
      'nova-senha-1',
    )
    await userEvent.click(salvar())

    expect(alterarMock).toHaveBeenCalledWith(7, {
      nome: 'Marcos Andrade',
      papeis: ['GES'],
      senha: 'nova-senha-1',
    })
  })

  it('não salva sem papel', async () => {
    setup(marcos)
    await userEvent.click(screen.getByLabelText('Gestor(a) de Emergências'))
    expect(salvar()).toBeDisabled()
  })
})
