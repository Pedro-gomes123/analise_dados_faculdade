import type { Content, TDocumentDefinitions } from 'pdfmake/interfaces';
import {
  type BlocoBoletim,
  type DocumentoBoletim,
  ORGAO,
  type SecaoDocumento,
  TITULO_DO_BOLETIM,
} from '@/modules/boletins/domain/documento-boletim';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

// Same document as the HTML preview (RN-009 #4, DEC-019); the font is set by
// the caller (infrastructure/pdf).
function blocoPdf(bloco: BlocoBoletim): Content {
  switch (bloco.tipo) {
    case 'paragrafo':
      return { text: bloco.texto, style: 'paragrafo' };
    case 'aviso':
      return { text: bloco.texto, style: 'aviso' };
    case 'lista':
      return { ul: bloco.itens, style: 'paragrafo' };
  }
}

function secaoPdf({ secao, titulo, blocos }: SecaoDocumento): Content[] {
  const estilo = secao === SecaoBoletim.Cabecalho ? 'titulo' : 'secao';
  return [{ text: titulo, style: estilo }, ...blocos.map(blocoPdf)];
}

export function definicaoPdf(
  documento: DocumentoBoletim,
  fonte: string,
): TDocumentDefinitions {
  return {
    info: {
      title: TITULO_DO_BOLETIM,
      author: ORGAO,
      creationDate: documento.geradoEm,
    },
    pageSize: 'A4',
    pageMargins: [40, 40, 40, 40],
    defaultStyle: { font: fonte, fontSize: 11, lineHeight: 1.3 },
    content: documento.secoes.flatMap(secaoPdf),
    styles: {
      titulo: {
        fontSize: 18,
        bold: true,
        color: '#1d4ed8',
        margin: [0, 0, 0, 4],
      },
      secao: { fontSize: 13, bold: true, margin: [0, 16, 0, 6] },
      paragrafo: { margin: [0, 2, 0, 2] },
      aviso: { italics: true, color: '#6b6b6b', margin: [0, 2, 0, 2] },
    },
  };
}

const dataIso = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Recife',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

// boletim-2026-11-02.pdf, with the date in Recife.
export function nomeDoArquivo(geradoEm: Date): string {
  return `boletim-${dataIso.format(geradoEm)}.pdf`;
}
