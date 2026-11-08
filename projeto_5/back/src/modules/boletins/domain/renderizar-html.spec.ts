import type { DocumentoBoletim } from '@/modules/boletins/domain/documento-boletim';
import {
  escaparHtml,
  renderizarHtml,
} from '@/modules/boletins/domain/renderizar-html';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

const DOCUMENTO: DocumentoBoletim = {
  geradoEm: new Date('2026-11-02T12:00:00Z'),
  secoes: [
    {
      secao: SecaoBoletim.Cabecalho,
      titulo: 'Boletim de Emergência Climática',
      blocos: [{ tipo: 'paragrafo', texto: 'Secretaria' }],
    },
    {
      secao: SecaoBoletim.AcoesAbrigos,
      titulo: 'Ações em curso e abrigos',
      blocos: [
        { tipo: 'lista', itens: ['<script>alert(1)</script>', 'B & "C"'] },
        { tipo: 'aviso', texto: 'Sem abrigos' },
      ],
    },
  ],
};

describe('escaparHtml', () => {
  it('escapes the HTML special characters', () => {
    expect(escaparHtml(`<a href="x">'&'</a>`)).toBe(
      '&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;',
    );
  });
});

describe('renderizarHtml', () => {
  const html = renderizarHtml(DOCUMENTO);

  it('is a complete page in Portuguese', () => {
    expect(html.startsWith('<!doctype html>')).toBe(true);
    expect(html).toContain('<html lang="pt-BR">');
    expect(html).toContain('<meta charset="utf-8">');
  });

  it('renders the header as h1 and the other sections as h2, in order', () => {
    expect(html).toContain(
      '<header data-secao="cabecalho"><h1>Boletim de Emergência Climática</h1><p>Secretaria</p></header>',
    );
    expect(html).toContain(
      '<section data-secao="acoes_abrigos"><h2>Ações em curso e abrigos</h2>',
    );
    expect(html.indexOf('<header')).toBeLessThan(html.indexOf('<section'));
  });

  it('escapes user text (action descriptions)', () => {
    expect(html).not.toContain('<script>');
    expect(html).toContain(
      '<ul><li>&lt;script&gt;alert(1)&lt;/script&gt;</li><li>B &amp; &quot;C&quot;</li></ul>',
    );
  });

  it('marks notices with their own class', () => {
    expect(html).toContain('<p class="aviso">Sem abrigos</p>');
  });
});
