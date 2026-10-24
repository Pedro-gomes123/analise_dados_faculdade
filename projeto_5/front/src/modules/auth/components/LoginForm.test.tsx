import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AxiosError, AxiosHeaders } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LoginForm } from '@/modules/auth/components/LoginForm'
import { login } from '@/modules/auth/service/auth.service'
import { getToken } from '@/modules/auth/session'
import type { Usuario } from '@/modules/auth/types'

vi.mock('@/modules/auth/service/auth.service', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))

const loginMock = vi.mocked(login)

const usuario: Usuario = {
  id: 1,
  nome: 'Marcos Andrade',
  email: 'marcos@exemplo.gov.br',
  papeis: ['GES'],
  ativo: true,
}

function erroHttp(status: number, message = 'erro') {
  return new AxiosError('falha', String(status), undefined, undefined, {
    status,
    statusText: '',
    headers: {},
    config: { headers: new AxiosHeaders() },
    data: { status_code: status, error: '', message },
  })
}

function setup() {
  const onSuccess = vi.fn()
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <LoginForm onSuccess={onSuccess} />
    </QueryClientProvider>,
  )
  return { onSuccess, client }
}

async function preencherEEnviar(email = ' marcos@exemplo.gov.br ', senha = 'senha-forte-1') {
  await userEvent.type(screen.getByLabelText('E-mail'), email)
  await userEvent.type(screen.getByLabelText('Senha'), senha)
  await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('LoginForm', () => {
  beforeEach(() => {
    loginMock.mockReset()
    localStorage.clear()
  })

  it('desabilita o botão até preencher e-mail e senha', () => {
    setup()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeDisabled()
  })

  it('guarda o token, preenche o usuário atual e avisa o sucesso', async () => {
    loginMock.mockResolvedValue({ access_token: 'jwt', usuario })
    const { onSuccess, client } = setup()

    await preencherEEnviar()

    expect(loginMock.mock.calls[0]?.[0]).toEqual({
      email: 'marcos@exemplo.gov.br',
      senha: 'senha-forte-1',
    })
    expect(onSuccess).toHaveBeenCalledWith(usuario)
    expect(getToken()).toBe('jwt')
    expect(client.getQueryData(['auth', 'me'])).toEqual(usuario)
  })

  it('mostra a mensagem única do FLX-001 no 401', async () => {
    loginMock.mockRejectedValue(erroHttp(401))
    const { onSuccess } = setup()

    await preencherEEnviar()

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos')
    expect(onSuccess).not.toHaveBeenCalled()
    expect(getToken()).toBeNull()
  })

  it('mostra a mensagem de validação do back no 422', async () => {
    loginMock.mockRejectedValue(erroHttp(422, 'E-mail inválido'))
    setup()

    await preencherEEnviar('nao-e-email')

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail inválido')
  })

  it('avisa quando o servidor não responde', async () => {
    loginMock.mockRejectedValue(new AxiosError('Network Error'))
    setup()

    await preencherEEnviar()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível conectar ao servidor',
    )
  })
})
