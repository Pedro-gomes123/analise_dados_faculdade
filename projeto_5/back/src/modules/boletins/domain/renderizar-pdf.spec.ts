import type { DocumentoBoletim } from '@/modules/boletins/domain/documento-boletim';
import {
  definicaoPdf,
  nomeDoArquivo,
} from '@/modules/boletins/domain/renderizar-pdf';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

const GERADO_EM = new Date('2026-11-02T12:00:00Z');

const DOCUMENTO: DocumentoBoletim = {
  geradoEm: GERADO_EM,
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
        { tipo: 'lista', itens: ['Ação 1', 'Ação 2'] },
        { tipo: 'aviso', texto: 'Sem abrigos' },
      ],
    },
  ],
};

describe('definicaoPdf (RN-009 #4, DEC-019)', () => {
  const definicao = definicaoPdf(DOCUMENTO, 'Helvetica');

  it('has the same sections and blocks as the document, in order', () => {
    expect(definicao.content).toEqual([
      { text: 'Boletim de Emergência Climática', style: 'titulo' },
      { text: 'Secretaria', style: 'paragrafo' },
      { text: 'Ações em curso e abrigos', style: 'secao' },
      { ul: ['Ação 1', 'Ação 2'], style: 'paragrafo' },
      { text: 'Sem abrigos', style: 'aviso' },
    ]);
  });

  it('uses the given font and fills the metadata', () => {
    expect(definicao.defaultStyle).toMatchObject({ font: 'Helvetica' });
    expect(definicao.info).toEqual({
      title: 'Boletim de Emergência Climática',
      author: 'Secretaria Executiva de Vigilância em Saúde do Recife',
      creationDate: GERADO_EM,
    });
    expect(definicao.pageSize).toBe('A4');
  });
});

describe('nomeDoArquivo', () => {
  it('uses the date in Recife', () => {
    expect(nomeDoArquivo(GERADO_EM)).toBe('boletim-2026-11-02.pdf');
    // 01:30 UTC is still the previous day in Recife (UTC-3).
    expect(nomeDoArquivo(new Date('2026-11-02T01:30:00Z'))).toBe(
      'boletim-2026-11-01.pdf',
    );
  });
});
