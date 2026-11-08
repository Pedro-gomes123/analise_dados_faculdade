import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TempoAcionamentoPanel } from '@/modules/indicadores/components/TempoAcionamentoPanel'
import { consultarTempoAcionamento } from '@/modules/indicadores/service/indicadores.service'
import type { TempoAcionamento } from '@/modules/indicadores/types'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/indicadores/service/indicadores.service', () => ({
  consultarTempoAcionamento: vi.fn(),
}))

const consultarMock = vi.mocked(consultarTempoAcionamento)

const dados: TempoAcionamento = {
  inicio: '2026-10-17T13:00:00Z',
  fim: '2026-10-24T13:00:00Z',
  media_segundos: 2280,
  alertas_com_acao: 1,
  alertas_sem_acao: 1,
  alertas: [
    {
      id: 10,
      variavel: 'chuva_1h',
      territorio: 'RPA-1',
      nivel: 'ALTO',
      disparado_em: '2026-10-24T13:00:00Z',
      primeira_acao_em: '2026-10-24T13:38:00Z',
      tempo_segundos: 2280,
    },
    {
      id: 11,
      variavel: 'nivel_rio',
      territorio: 'RPA-2',
      nivel: 'MEDIO',
      disparado_em: '2026-10-24T14:00:00Z',
      primeira_acao_em: null,
      tempo_segundos: null,
    },
  ],
}

const horasDoIntervalo = (call: number) => {
  const { inicio, fim } = consultarMock.mock.calls[call]![0]
  return (Date.parse(fim) - Date.parse(inicio)) / 3_600_000
}

describe('TempoAcionamentoPanel (REQ-018, RN-006)', () => {
  beforeEach(() => {
    consultarMock.mockReset()
    consultarMock.mockResolvedValue(dados)
  })

  it('mostra a média e os alertas sem ação à parte (PR-021)', async () => {
    renderWithQuery(<TempoAcionamentoPanel />)

    expect(await screen.findByText('38 min', { selector: 'p' })).toBeInTheDocument()
    const semAcao = screen.getByText('Alertas sem ação').closest('div')!.parentElement!
    expect(within(semAcao).getByText('1')).toBeInTheDocument()
    expect(within(semAcao).getByText('Fora da média')).toBeInTheDocument()
  })

  it('lista cada alerta com o seu tempo, ou "Sem ação"', async () => {
    renderWithQuery(<TempoAcionamentoPanel />)

    const comAcao = (await screen.findByText('RPA-1')).closest('tr')!
    expect(within(comAcao).getByText('24/10/2026 10:38')).toBeInTheDocument()
    expect(within(comAcao).getByText('38 min')).toBeInTheDocument()

    const semAcao = screen.getByText('RPA-2').closest('tr')!
    expect(within(semAcao).getByText('Sem ação')).toBeInTheDocument()
    expect(within(semAcao).getByText('—')).toBeInTheDocument()
  })

  it('começa em 7 dias e troca o período (PR-018)', async () => {
    renderWithQuery(<TempoAcionamentoPanel />)
    await screen.findByText('RPA-1')
    expect(horasDoIntervalo(0)).toBe(24 * 7)

    await userEvent.click(screen.getByRole('tab', { name: '30 dias' }))
    expect(horasDoIntervalo(consultarMock.mock.calls.length - 1)).toBe(24 * 30)
  })

  it('sem alerta no período, a média fica em branco', async () => {
    consultarMock.mockResolvedValue({
      ...dados,
      media_segundos: null,
      alertas_com_acao: 0,
      alertas_sem_acao: 0,
      alertas: [],
    })
    renderWithQuery(<TempoAcionamentoPanel />)

    expect(await screen.findByText('Nenhum alerta no período.')).toBeInTheDocument()
    expect(screen.getByText('—', { selector: 'p' })).toBeInTheDocument()
  })
})
