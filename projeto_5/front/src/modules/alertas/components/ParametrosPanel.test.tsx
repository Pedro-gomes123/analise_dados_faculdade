import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Paginated } from '@/lib/pagination'
import { ParametrosPanel } from '@/modules/alertas/components/ParametrosPanel'
import {
  alterarParametro,
  criarParametro,
  listarHistorico,
  listarParametros,
} from '@/modules/alertas/service/alertas.service'
import type { HistoricoParametro, ParametroAlerta } from '@/modules/alertas/types'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/alertas/service/alertas.service', () => ({
  listarParametros: vi.fn(),
  listarHistorico: vi.fn(),
  criarParametro: vi.fn(),
  alterarParametro: vi.fn(),
}))

const listarMock = vi.mocked(listarParametros)
const historicoMock = vi.mocked(listarHistorico)
const criarMock = vi.mocked(criarParametro)
const alterarMock = vi.mocked(alterarParametro)

const parametro: ParametroAlerta = {
  id: 3,
  variavel: 'chuva_1h',
  territorio: 'RPA-1',
  limiar: 50,
  nivel: 'ALTO',
  ativo: true,
  atualizado_em: '2026-10-24T13:00:00Z',
}

function pagina<T>(data: T[]): Paginated<T> {
  return { data, meta: { itemsPerPage: 20, totalItems: data.length, currentPage: 1, totalPages: 1 } }
}

describe('ParametrosPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listarMock.mockResolvedValue(pagina([parametro]))
  })

  it('o Técnico só consulta: sem criar, editar ou inativar (PER-004)', async () => {
    renderWithQuery(<ParametrosPanel podeEditar={false} />)

    await screen.findByText('chuva_1h')
    expect(screen.queryByRole('button', { name: 'Novo parâmetro' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Inativar' })).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Histórico de chuva_1h em RPA-1' }),
    ).toBeInTheDocument()
  })

  it('o Gestor cria um parâmetro com limiar em pt-BR (PER-005)', async () => {
    criarMock.mockResolvedValue({ ...parametro, id: 4 })
    renderWithQuery(<ParametrosPanel podeEditar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Novo parâmetro' }))
    const dialogo = screen.getByRole('dialog')
    await userEvent.type(within(dialogo).getByLabelText('Variável'), 'nivel_rio')
    await userEvent.type(within(dialogo).getByLabelText('Território'), 'RPA-2')
    await userEvent.type(within(dialogo).getByLabelText('Limiar'), '3,25')
    await userEvent.type(within(dialogo).getByLabelText('Nível'), 'MEDIO')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }))

    expect(criarMock.mock.calls[0]?.[0]).toEqual({
      variavel: 'nivel_rio',
      territorio: 'RPA-2',
      limiar: 3.25,
      nivel: 'MEDIO',
    })
  })

  it('não deixa salvar limiar que não é número', async () => {
    renderWithQuery(<ParametrosPanel podeEditar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Novo parâmetro' }))
    const dialogo = screen.getByRole('dialog')
    await userEvent.type(within(dialogo).getByLabelText('Variável'), 'x')
    await userEvent.type(within(dialogo).getByLabelText('Território'), 'y')
    await userEvent.type(within(dialogo).getByLabelText('Limiar'), 'abc')
    await userEvent.type(within(dialogo).getByLabelText('Nível'), 'z')

    expect(within(dialogo).getByText('Informe um número')).toBeInTheDocument()
    expect(within(dialogo).getByRole('button', { name: 'Salvar' })).toBeDisabled()
  })

  it('edita só limiar e nível; variável e território ficam travados', async () => {
    alterarMock.mockResolvedValue({ ...parametro, limiar: 60 })
    renderWithQuery(<ParametrosPanel podeEditar />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Editar chuva_1h em RPA-1' }),
    )
    const dialogo = screen.getByRole('dialog')
    expect(within(dialogo).getByLabelText('Variável')).toBeDisabled()
    expect(within(dialogo).getByLabelText('Território')).toBeDisabled()

    const limiar = within(dialogo).getByLabelText('Limiar')
    await userEvent.clear(limiar)
    await userEvent.type(limiar, '60')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }))

    expect(alterarMock).toHaveBeenCalledWith(3, { limiar: 60, nivel: 'ALTO' })
  })

  it('inativa só depois de confirmar (DEC-014)', async () => {
    alterarMock.mockResolvedValue({ ...parametro, ativo: false })
    renderWithQuery(<ParametrosPanel podeEditar />)

    await userEvent.click(await screen.findByRole('button', { name: 'Inativar' }))
    expect(alterarMock).not.toHaveBeenCalled()
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Inativar' }))

    expect(alterarMock).toHaveBeenCalledWith(3, { ativo: false })
  })

  it('mostra o histórico com autor e antes → depois (RN-001)', async () => {
    const item: HistoricoParametro = {
      id: 1,
      operacao: 'ALTERACAO',
      valor_anterior: { limiar: 50 },
      valor_novo: { limiar: 60 },
      autor: { id: 2, nome: 'Camila Rocha' },
      registrado_em: '2026-10-24T13:00:00Z',
    }
    historicoMock.mockResolvedValue(pagina([item]))
    renderWithQuery(<ParametrosPanel podeEditar={false} />)

    await userEvent.click(
      await screen.findByRole('button', { name: 'Histórico de chuva_1h em RPA-1' }),
    )
    const dialogo = screen.getByRole('dialog')

    expect(await within(dialogo).findByText('Limiar: 50 → 60')).toBeInTheDocument()
    expect(within(dialogo).getByText('Camila Rocha · 24/10/2026 10:00')).toBeInTheDocument()
    expect(historicoMock).toHaveBeenCalledWith(3, 1)
  })
})
