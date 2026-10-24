import {
  type BlocoBoletim,
  type DocumentoBoletim,
  type SecaoDocumento,
  TITULO_DO_BOLETIM,
} from '@/modules/boletins/domain/documento-boletim';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

const ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

// Action descriptions are user input: everything is escaped.
export function escaparHtml(texto: string): string {
  return texto.replace(/[&<>"']/g, (caractere) => ESCAPES[caractere]);
}

// Self-contained page (inline style), so the front can show it in an iframe.
const ESTILO = `
body { font-family: Arial, Helvetica, sans-serif; color: #1a1a1a; margin: 32px; line-height: 1.5; }
header { border-bottom: 2px solid #1d4ed8; margin-bottom: 24px; padding-bottom: 8px; }
h1 { font-size: 22px; margin: 0 0 4px; color: #1d4ed8; }
h2 { font-size: 16px; margin: 24px 0 8px; }
p { margin: 4px 0; }
ul { margin: 4px 0; padding-left: 20px; }
.aviso { color: #6b6b6b; font-style: italic; }
`;

function renderizarBloco(bloco: BlocoBoletim): string {
  switch (bloco.tipo) {
    case 'paragrafo':
      return `<p>${escaparHtml(bloco.texto)}</p>`;
    case 'aviso':
      return `<p class="aviso">${escaparHtml(bloco.texto)}</p>`;
    case 'lista':
      return `<ul>${bloco.itens.map((item) => `<li>${escaparHtml(item)}</li>`).join('')}</ul>`;
  }
}

function renderizarSecao({ secao, titulo, blocos }: SecaoDocumento): string {
  const conteudo = blocos.map(renderizarBloco).join('');
  return secao === SecaoBoletim.Cabecalho
    ? `<header data-secao="${secao}"><h1>${escaparHtml(titulo)}</h1>${conteudo}</header>`
    : `<section data-secao="${secao}"><h2>${escaparHtml(titulo)}</h2>${conteudo}</section>`;
}

export function renderizarHtml(documento: DocumentoBoletim): string {
  return [
    '<!doctype html>',
    '<html lang="pt-BR">',
    '<head>',
    '<meta charset="utf-8">',
    `<title>${TITULO_DO_BOLETIM}</title>`,
    `<style>${ESTILO}</style>`,
    '</head>',
    '<body>',
    ...documento.secoes.map(renderizarSecao),
    '</body>',
    '</html>',
  ].join('\n');
}
