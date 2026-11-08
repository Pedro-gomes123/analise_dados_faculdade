import {
  ORDEM_SECOES,
  SecaoBoletim,
} from '@/modules/boletins/enums/secao-boletim.enum';

// One structure for the HTML preview and the PDF (DEC-019, RN-009 #4).
export type BlocoBoletim =
  | { tipo: 'paragrafo'; texto: string }
  | { tipo: 'aviso'; texto: string }
  | { tipo: 'lista'; itens: string[] };

export interface SecaoDocumento {
  secao: SecaoBoletim;
  titulo: string;
  blocos: BlocoBoletim[];
}

export interface DocumentoBoletim {
  geradoEm: Date;
  secoes: SecaoDocumento[];
}

export interface AcaoBoletim {
  descricao: string;
  autor: string;
  registradaEm: Date;
  idAlerta: number | null;
}

export interface DadosBoletim {
  geradoEm: Date;
  acoes: AcaoBoletim[];
}

// PR-022 b.
export const JANELA_ACOES_MS = 24 * 60 * 60 * 1000;

export const TITULO_DO_BOLETIM = 'Boletim de Emergência Climática';
export const ORGAO = 'Secretaria Executiva de Vigilância em Saúde do Recife';

const TITULO_SECAO: Record<SecaoBoletim, string> = {
  [SecaoBoletim.Cabecalho]: TITULO_DO_BOLETIM,
  [SecaoBoletim.Meteorologia]: 'Situação meteorológica',
  [SecaoBoletim.Rios]: 'Nível dos rios e cotas de alerta',
  [SecaoBoletim.RiscosSaude]: 'Riscos à saúde e recomendações',
  [SecaoBoletim.AcoesAbrigos]: 'Ações em curso e abrigos',
  [SecaoBoletim.Contatos]: 'Contatos de emergência',
};

// PR-022 c: no source yet, so the section says so instead of inventing text.
const SEM_DADOS_INTEGRADOS =
  'Conteúdo indisponível: estes dados ainda não estão integrados ao sistema.';
const SEM_ORIGEM_DEFINIDA =
  'Conteúdo indisponível: a origem deste conteúdo ainda não foi definida.';
const SEM_ABRIGOS =
  'Informações de abrigos ainda não estão disponíveis no sistema.';

const dataHora = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Recife',
  dateStyle: 'short',
  timeStyle: 'short',
});

export function formatarDataHora(data: Date): string {
  return dataHora.format(data);
}

// RN-009 #1 order; a repeated section enters once (PR-022 d).
export function ordenarSecoes(secoes: readonly SecaoBoletim[]): SecaoBoletim[] {
  return ORDEM_SECOES.filter((secao) => secoes.includes(secao));
}

function descreverAcao(acao: AcaoBoletim): string {
  const alerta = acao.idAlerta === null ? '' : `, alerta nº ${acao.idAlerta}`;
  return `${formatarDataHora(acao.registradaEm)}: ${acao.descricao} (${acao.autor}${alerta})`;
}

function blocosDaSecao(
  secao: SecaoBoletim,
  dados: DadosBoletim,
): BlocoBoletim[] {
  switch (secao) {
    case SecaoBoletim.Cabecalho:
      return [
        { tipo: 'paragrafo', texto: ORGAO },
        {
          tipo: 'paragrafo',
          texto: `Gerado em ${formatarDataHora(dados.geradoEm)}`,
        },
      ];
    case SecaoBoletim.Meteorologia:
    case SecaoBoletim.Rios:
      return [{ tipo: 'aviso', texto: SEM_DADOS_INTEGRADOS }];
    case SecaoBoletim.RiscosSaude:
    case SecaoBoletim.Contatos:
      return [{ tipo: 'aviso', texto: SEM_ORIGEM_DEFINIDA }];
    case SecaoBoletim.AcoesAbrigos:
      return [
        dados.acoes.length === 0
          ? {
              tipo: 'paragrafo',
              texto: 'Nenhuma ação registrada nas últimas 24 horas.',
            }
          : { tipo: 'lista', itens: dados.acoes.map(descreverAcao) },
        { tipo: 'aviso', texto: SEM_ABRIGOS },
      ];
  }
}

export function montarDocumentoBoletim(
  secoes: readonly SecaoBoletim[],
  dados: DadosBoletim,
): DocumentoBoletim {
  return {
    geradoEm: dados.geradoEm,
    secoes: ordenarSecoes(secoes).map((secao) => ({
      secao,
      titulo: TITULO_SECAO[secao],
      blocos: blocosDaSecao(secao, dados),
    })),
  };
}
