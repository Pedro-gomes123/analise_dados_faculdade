import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { baixarArquivo } from '@/lib/download'
import { ComposicaoBoletim } from '@/modules/boletins/components/ComposicaoBoletim'
import {
  gerarBoletimPdf,
  preVisualizarBoletim,
} from '@/modules/boletins/service/boletins.service'
import { apiError } from '@/test/api-error'
import { renderWithQuery } from '@/test/render'

vi.mock('@/modules/boletins/service/boletins.service', () => ({
  preVisualizarBoletim: vi.fn(),
  gerarBoletimPdf: vi.fn(),
}))

vi.mock('@/lib/download', () => ({ baixarArquivo: vi.fn() }))

const previaMock = vi.mocked(preVisualizarBoletim)
const pdfMock = vi.mocked(gerarBoletimPdf)
const baixarMock = vi.mocked(baixarArquivo)

const HTML = '<!doctype html><h1>Boletim de Emergência Climática</h1>'
const TODAS = ['cabecalho', 'meteorologia', 'rios', 'riscos_saude', 'acoes_abrigos', 'contatos']

const botaoPrevia = () => screen.getByRole('button', { name: /pré-visualizar/i })
const botaoPdf = () => screen.getByRole('button', { name: /gerar boletim/i })

describe('ComposicaoBoletim (FLX-004, RN-009)', () => {
  beforeEach(() => {
    previaMock.mockReset()
    pdfMock.mockReset()
    baixarMock.mockReset()
    previaMock.mockResolvedValue(HTML)
  })

  it('começa com todas as seções e só libera o PDF depois da pré-visualização', () => {
    renderWithQuery(<ComposicaoBoletim />)

    for (const caixa of screen.getAllByRole('checkbox')) {
      expect(caixa).toBeChecked()
    }
    expect(screen.getByText('Escolha as seções e clique em Pré-visualizar.')).toBeInTheDocument()
    expect(botaoPdf()).toBeDisabled()
  })

  it('pré-visualiza as seções escolhidas, na ordem da RN-009', async () => {
    renderWithQuery(<ComposicaoBoletim />)

    await userEvent.click(screen.getByRole('checkbox', { name: 'Situação meteorológica' }))
    await userEvent.click(botaoPrevia())

    expect(previaMock.mock.calls[0]![0]).toEqual(TODAS.filter((s) => s !== 'meteorologia'))
    const iframe = await screen.findByTitle('Pré-visualização do boletim')
    expect(iframe).toHaveAttribute('srcdoc', HTML)
    expect(iframe).toHaveAttribute('sandbox', '')
  })

  it('gera o PDF com as mesmas seções e baixa o arquivo (RN-009 #4)', async () => {
    const arquivo = new Blob(['%PDF-'], { type: 'application/pdf' })
    pdfMock.mockResolvedValue({ nome: 'boletim-2026-11-02.pdf', arquivo })
    renderWithQuery(<ComposicaoBoletim />)

    await userEvent.click(botaoPrevia())
    await screen.findByTitle('Pré-visualização do boletim')
    await userEvent.click(botaoPdf())

    expect(pdfMock.mock.calls[0]![0]).toEqual(TODAS)
    await vi.waitFor(() =>
      expect(baixarMock).toHaveBeenCalledWith(arquivo, 'boletim-2026-11-02.pdf'),
    )
  })

  it('mudar as seções descarta a pré-visualização', async () => {
    renderWithQuery(<ComposicaoBoletim />)
    await userEvent.click(botaoPrevia())
    await screen.findByTitle('Pré-visualização do boletim')

    await userEvent.click(screen.getByRole('checkbox', { name: 'Contatos de emergência' }))

    expect(screen.queryByTitle('Pré-visualização do boletim')).not.toBeInTheDocument()
    expect(botaoPdf()).toBeDisabled()
  })

  it('sem seção, não deixa pré-visualizar (RN-009 #2)', async () => {
    renderWithQuery(<ComposicaoBoletim />)

    for (const caixa of screen.getAllByRole('checkbox')) await userEvent.click(caixa)

    expect(screen.getByText('Escolha ao menos uma seção.')).toBeInTheDocument()
    expect(botaoPrevia()).toBeDisabled()
  })

  it('mostra o erro da API', async () => {
    previaMock.mockRejectedValue(
      apiError(422, {
        message: 'Dados inválidos',
        errors: [
          { property: 'secoes', constraints: { isEnum: 'Escolha ao menos uma seção válida' } },
        ],
      }),
    )
    renderWithQuery(<ComposicaoBoletim />)

    await userEvent.click(botaoPrevia())

    expect(await screen.findByText('Escolha ao menos uma seção válida')).toBeInTheDocument()
  })
})
