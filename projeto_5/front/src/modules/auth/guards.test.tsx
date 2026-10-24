import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, createRouter, RouterProvider } from '@tanstack/react-router'
import { render, screen } from '@testing-library/react'
import { AxiosError } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getMe } from '@/modules/auth/service/auth.service'
import { getToken, setToken } from '@/modules/auth/session'
import type { Papel } from '@/modules/auth/types'
import { routeTree } from '@/routeTree.gen'

vi.mock('@/modules/auth/service/auth.service', () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}))

vi.mock('@/modules/usuarios/service/usuarios.service', () => ({
  listarUsuarios: vi.fn(() => new Promise(() => {})),
}))

vi.mock('@/modules/health/components/ApiStatus', () => ({
  ApiStatus: () => null,
}))

const getMeMock = vi.mocked(getMe)

function logado(papeis: Papel[]) {
  setToken('jwt')
  getMeMock.mockResolvedValue({ id: 1, nome: 'Marcos', email: 'm@x.gov.br', papeis, ativo: true })
}

async function abrir(caminho: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [caminho] }),
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  await router.load()
  return router
}

describe('guarda de rotas', () => {
  beforeEach(() => {
    getMeMock.mockReset()
    localStorage.clear()
  })

  it('manda para o login quem não está logado', async () => {
    const router = await abrir('/estacoes/est-01')

    expect(router.state.location.pathname).toBe('/login')
    expect(getMeMock).not.toHaveBeenCalled()
  })

  it('abre a estação do papel a partir da raiz', async () => {
    logado(['GES'])
    const router = await abrir('/')

    expect(router.state.location.pathname).toBe('/estacoes/est-02')
    expect(await screen.findByText('EST-02 · Gestor(a) de Emergências')).toBeInTheDocument()
  })

  it('devolve para a própria estação quem abre a estação de outro papel', async () => {
    logado(['COM'])
    const router = await abrir('/estacoes/est-01')

    expect(router.state.location.pathname).toBe('/estacoes/est-04')
  })

  it('tira do login quem já está logado', async () => {
    logado(['ADM'])
    const router = await abrir('/login')

    expect(router.state.location.pathname).toBe('/usuarios')
  })

  it('apaga o token e volta ao login quando o back recusa o token', async () => {
    setToken('expirado')
    getMeMock.mockRejectedValue(new AxiosError('Unauthorized', '401'))
    const router = await abrir('/estacoes/est-01')

    expect(router.state.location.pathname).toBe('/login')
    expect(getToken()).toBeNull()
  })
})
