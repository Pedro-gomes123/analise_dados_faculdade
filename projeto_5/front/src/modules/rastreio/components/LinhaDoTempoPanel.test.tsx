import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listarAlertas } from '@/modules/alertas/service/alertas.service'
import type { Alerta } from '@/modules/alertas/types'
import { LinhaDoTempoPanel } from '@/modules/rastreio/components/LinhaDoTempoPanel'
import { consultarLinhaDoTempo, criarAcao } from '@/modules/rastreio/service/rastreio.service'
import type { Acao, LinhaDoTempo } from '@/modules/rastreio/types'
import { apiError } from '@/test/api-error'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/alertas/service/alertas.service', () => ({ listarAlertas: vi.fn() }))
vi.mock('@/modules/rastreio/service/rastreio.service', () => ({
  consultarLinhaDoTempo: vi.fn(),
  criarAcao: vi.fn(),
}))

const listarAlertasMock = vi.mocked(listarAlertas)
const linhaMock = vi.mocked(consultarLinhaDoTempo)
const criarMock = vi.mocked(criarAcao)

const alertaAtivo: Alerta = {
  id: 10,
  nivel: 'ALTO',
  parametro: { id: 3, variavel: 'chuva_1h', limiar: 50 },
  territorio: 'RPA-1',
  valor_lido: 62.5,
  fonte: 'APAC',
  lida_em: '2026-10-24T12:55:00Z',
  disparado_em: '2026-10-24T13:00:00Z',
  fonte_atualizada_em: null,
  status: 'ATIVO',
}

const acao: Acao = {
  id: 7,
  descricao: 'Equipe enviada',
  id_alerta: 10,
  autor: { id: 2, nome: 'Camila Rocha' },
  registrada_em: '2026-10-24T13:20:00Z',
}

const linha: LinhaDoTempo = {
  inicio: '2026-10-23T13:30:00Z',
  fim: '2026-10-24T13:30:00Z',
  itens: [
    {
      tipo: 'ALERTA',
      em: '2026-10-24T13:00:00Z',
      alerta: {
        id: 10,
        variavel: 'chuva_1h',
        territorio: 'RPA-1',
        nivel: 'ALTO',
        limiar: 50,
        valor_lido: 62.5,
        lida_em: '2026-10-24T12:55:00Z',
        status: 'ATIVO',
      },
    },
    {
      tipo: 'ACAO',
      em: '2026-10-24T13:20:00Z',
      acao,
    },
  ],
}

describe('LinhaDoTempoPanel (REQ-006, FLX-003)', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    listarAlertasMock.mockResolvedValue({
      data: [alertaAtivo],
      meta: { itemsPerPage: 20, totalItems: 1, currentPage: 1, totalPages: 1 },
    })
    linhaMock.mockResolvedValue(linha)
  })

  it('mostra alertas e ações em ordem, com horário do Recife e autor (RN-005)', async () => {
    renderWithQuery(<LinhaDoTempoPanel podeRegistrar={false} />)

    const lista = await screen.findByRole('list', { name: 'Linha do tempo' })
    const itens = within(lista).getAllByRole('listitem')
    expect(itens[0]).toHaveTextContent('24/10/2026 10:00')
    expect(itens[0]).toHaveTextContent('Alerta ALTO · chuva_1h em RPA-1')
    expect(itens[1]).toHaveTextContent('Equipe enviada — Camila Rocha · alerta #10')
  })

  it('consulta as últimas 24 h e troca o período (PR-018)', async () => {
    renderWithQuery(<LinhaDoTempoPanel podeRegistrar={false} />)
    await screen.findByRole('list', { name: 'Linha do tempo' })

    const [primeiro] = linhaMock.mock.calls[0]!
    const horas = (Date.parse(primeiro.fim) - Date.parse(primeiro.inicio)) / 3_600_000
    expect(horas).toBe(24)

    await userEvent.click(screen.getByRole('tab', { name: '7 dias' }))
    const ultimo = linhaMock.mock.calls.at(-1)![0]
    expect((Date.parse(ultimo.fim) - Date.parse(ultimo.inicio)) / 3_600_000).toBe(24 * 7)
  })

  it('sem PER-007 não mostra o formulário', async () => {
    renderWithQuery(<LinhaDoTempoPanel podeRegistrar={false} />)
    await screen.findByRole('list', { name: 'Linha do tempo' })

    expect(screen.queryByRole('button', { name: 'Registrar ação' })).not.toBeInTheDocument()
  })

  it('registra ação ligada a um alerta ativo e atualiza a linha do tempo', async () => {
    criarMock.mockResolvedValue(acao)
    renderWithQuery(<LinhaDoTempoPanel podeRegistrar />)
    await screen.findByRole('list', { name: 'Linha do tempo' })
    const consultasAntes = linhaMock.mock.calls.length

    await userEvent.type(screen.getByLabelText('O que foi feito'), '  Equipe enviada ')
    await userEvent.selectOptions(
      await screen.findByLabelText('Alerta relacionado'),
      '#10 · ALTO · chuva_1h em RPA-1',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Registrar ação' }))

    expect(criarMock.mock.calls[0]?.[0]).toEqual({ descricao: 'Equipe enviada', id_alerta: 10 })
    expect(await screen.findByRole('status')).toHaveTextContent('Ação registrada.')
    expect(screen.getByLabelText('O que foi feito')).toHaveValue('')
    expect(linhaMock.mock.calls.length).toBeGreaterThan(consultasAntes)
  })

  it('registra ação sem alerta e mostra o erro da API', async () => {
    criarMock.mockRejectedValue(apiError(404, { message: 'Alerta não encontrado' }))
    renderWithQuery(<LinhaDoTempoPanel podeRegistrar />)

    await userEvent.type(await screen.findByLabelText('O que foi feito'), 'Abrigo aberto')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar ação' }))

    expect(criarMock.mock.calls[0]?.[0]).toEqual({ descricao: 'Abrigo aberto' })
    expect(await screen.findByRole('alert')).toHaveTextContent('Alerta não encontrado')
  })
})
