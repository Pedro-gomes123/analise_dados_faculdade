// POST /boletins/pre-visualizacao e /boletins/pdf (MOD-004, RN-009).
export type SecaoBoletim =
  | 'cabecalho'
  | 'meteorologia'
  | 'rios'
  | 'riscos_saude'
  | 'acoes_abrigos'
  | 'contatos'

// RN-009 #1: a ordem desta lista é a ordem do boletim.
export const SECOES_BOLETIM: { valor: SecaoBoletim; rotulo: string }[] = [
  { valor: 'cabecalho', rotulo: 'Cabeçalho institucional' },
  { valor: 'meteorologia', rotulo: 'Situação meteorológica' },
  { valor: 'rios', rotulo: 'Nível dos rios e cotas de alerta' },
  { valor: 'riscos_saude', rotulo: 'Riscos à saúde e recomendações' },
  { valor: 'acoes_abrigos', rotulo: 'Ações em curso e abrigos' },
  { valor: 'contatos', rotulo: 'Contatos de emergência' },
]

export interface BoletimPdf {
  nome: string
  arquivo: Blob
}
