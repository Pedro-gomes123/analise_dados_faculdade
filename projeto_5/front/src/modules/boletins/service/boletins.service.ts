import axios from 'axios'
import { http } from '@/lib/http'
import type { BoletimPdf, SecaoBoletim } from '@/modules/boletins/types'

const NOME_PADRAO = 'boletim.pdf'

export async function preVisualizarBoletim(secoes: SecaoBoletim[]): Promise<string> {
  const { data } = await http.post<string>(
    '/boletins/pre-visualizacao',
    { secoes },
    { responseType: 'text' },
  )
  return data
}

// attachment; filename="boletim-2026-11-02.pdf"
export function nomeDoAnexo(disposicao: unknown): string {
  if (typeof disposicao !== 'string') return NOME_PADRAO
  return /filename="([^"]+)"/.exec(disposicao)?.[1] ?? NOME_PADRAO
}

export async function gerarBoletimPdf(secoes: SecaoBoletim[]): Promise<BoletimPdf> {
  try {
    const { data, headers } = await http.post<Blob>(
      '/boletins/pdf',
      { secoes },
      { responseType: 'blob' },
    )
    return { nome: nomeDoAnexo(headers['content-disposition']), arquivo: data }
  } catch (error) {
    // Com responseType blob, o corpo de erro (JSON, DEC-010) também chega como
    // Blob; vira objeto de novo para describeApiError ler a mensagem.
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
      try {
        error.response.data = JSON.parse(await error.response.data.text())
      } catch {
        // Corpo que não é JSON: fica a mensagem genérica.
      }
    }
    throw error
  }
}
