import { AxiosError, AxiosHeaders } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { describeApiError, http } from '@/lib/http'
import { gerarBoletimPdf, nomeDoAnexo } from '@/modules/boletins/service/boletins.service'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('nomeDoAnexo', () => {
  it('lê o nome do Content-Disposition', () => {
    expect(nomeDoAnexo('attachment; filename="boletim-2026-11-02.pdf"')).toBe(
      'boletim-2026-11-02.pdf',
    )
  })

  it('usa um nome padrão sem o cabeçalho', () => {
    expect(nomeDoAnexo(undefined)).toBe('boletim.pdf')
    expect(nomeDoAnexo('attachment')).toBe('boletim.pdf')
  })
})

describe('gerarBoletimPdf', () => {
  it('devolve o arquivo e o nome', async () => {
    const arquivo = new Blob(['%PDF-'])
    const post = vi.spyOn(http, 'post').mockResolvedValue({
      data: arquivo,
      headers: { 'content-disposition': 'attachment; filename="boletim-2026-11-02.pdf"' },
    })

    expect(await gerarBoletimPdf(['cabecalho'])).toEqual({
      nome: 'boletim-2026-11-02.pdf',
      arquivo,
    })
    expect(post).toHaveBeenCalledWith(
      '/boletins/pdf',
      { secoes: ['cabecalho'] },
      { responseType: 'blob' },
    )
  })

  it('converte o corpo de erro em Blob para JSON (DEC-010)', async () => {
    const corpo = {
      status_code: 422,
      message: 'Dados inválidos',
      errors: [{ property: 'secoes', constraints: { isEnum: 'Escolha ao menos uma seção válida' } }],
    }
    vi.spyOn(http, 'post').mockRejectedValue(
      new AxiosError('falha', '422', undefined, undefined, {
        status: 422,
        statusText: '',
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: new Blob([JSON.stringify(corpo)], { type: 'application/json' }),
      }),
    )

    const erro: unknown = await gerarBoletimPdf(['cabecalho']).catch((e: unknown) => e)

    expect(describeApiError(erro)).toBe('Escolha ao menos uma seção válida')
  })
})
