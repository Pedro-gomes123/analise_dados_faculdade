import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Paginated } from '@/lib/pagination'
import { AlertasPanel } from '@/modules/alertas/components/AlertasPanel'
import { listarAlertas } from '@/modules/alertas/service/alertas.service'
import type { Alerta } from '@/modules/alertas/types'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/alertas/service/alertas.service', () => ({ listarAlertas: vi.fn() }))

const listarMock = vi.mocked(listarAlertas)

const alerta: Alerta = {
  id: 10,
  nivel: 'ALTO',
  parametro: { id: 3, variavel: 'chuva_1h', limiar: 50 },
  territorio: 'RPA-1',
  valor_lido: 62.5,
  fonte: 'APAC',
  lida_em: '2026-10-24T13:00:00Z',
  disparado_em: '2026-10-24T13:05:00Z',
  fonte_atualizada_em: null,
  status: 'ATIVO',
}

function pagina(data: Alerta[]): Paginated<Alerta> {
  return { data, meta: { itemsPerPage: 20, totalItems: data.length, currentPage: 1, totalPages: 1 } }
}

describe('AlertasPanel (MOD-002, PR-009)', () => {
  beforeEach(() => {
    listarMock.mockReset()
    listarMock.mockResolvedValue(pagina([alerta]))
  })

  it('mostra os ativos por padrão, com leitura, limiar e horários do Recife', async () => {
    renderWithQuery(<AlertasPanel />)

    const linha = (await screen.findByText('RPA-1')).closest('tr')!
    expect(within(linha).getByText('ALTO')).toBeInTheDocument()
    expect(within(linha).getByText('62,5')).toBeInTheDocument()
    expect(within(linha).getByText('/ 50')).toBeInTheDocument()
    expect(within(linha).getByText('24/10/2026 10:05')).toBeInTheDocument()
    expect(listarMock).toHaveBeenCalledWith({ page: 1, status: 'ATIVO' })
  })

  it('troca para o histórico de encerrados e para todos', async () => {
    renderWithQuery(<AlertasPanel />)
    await screen.findByText('RPA-1')

    await userEvent.click(screen.getByRole('tab', { name: 'Encerrados' }))
    expect(listarMock).toHaveBeenLastCalledWith({ page: 1, status: 'ENCERRADO' })

    await userEvent.click(screen.getByRole('tab', { name: 'Todos' }))
    expect(listarMock).toHaveBeenLastCalledWith({ page: 1, status: undefined })
  })

  it('avisa quando não há alertas', async () => {
    listarMock.mockResolvedValue(pagina([]))
    renderWithQuery(<AlertasPanel />)

    expect(await screen.findByText('Nenhum alerta encontrado.')).toBeInTheDocument()
  })
})
