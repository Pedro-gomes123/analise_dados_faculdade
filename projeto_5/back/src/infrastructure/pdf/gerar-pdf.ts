import pdfmake from 'pdfmake';
import type { TDocumentDefinitions } from 'pdfmake/interfaces';

// DEC-019. PDF standard fonts (no font files to ship). They cover the
// Portuguese accents (WinAnsi encoding).
const FONTE_PADRAO = {
  normal: 'Helvetica',
  bold: 'Helvetica-Bold',
  italics: 'Helvetica-Oblique',
  bolditalics: 'Helvetica-BoldOblique',
};
const FONTES_PERMITIDAS = new Set(Object.values(FONTE_PADRAO));

export const FONTE = 'Helvetica';

pdfmake.setFonts({ [FONTE]: FONTE_PADRAO });
// Nothing in a document may read local files or URLs (images, fonts): only the
// standard font names above pass the local policy.
pdfmake.setLocalAccessPolicy((caminho) => FONTES_PERMITIDAS.has(caminho));
pdfmake.setUrlAccessPolicy(() => false);

export function gerarPdf(definicao: TDocumentDefinitions): Promise<Buffer> {
  return pdfmake.createPdf(definicao).getBuffer();
}
