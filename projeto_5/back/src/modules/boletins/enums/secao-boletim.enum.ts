// RN-009 #1. Declaration order is the order of the sections in the bulletin.
export enum SecaoBoletim {
  Cabecalho = 'cabecalho',
  Meteorologia = 'meteorologia',
  Rios = 'rios',
  RiscosSaude = 'riscos_saude',
  AcoesAbrigos = 'acoes_abrigos',
  Contatos = 'contatos',
}

export const ORDEM_SECOES: readonly SecaoBoletim[] =
  Object.values(SecaoBoletim);
