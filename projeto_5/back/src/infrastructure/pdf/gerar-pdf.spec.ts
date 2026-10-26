import { FONTE, gerarPdf } from '@/infrastructure/pdf/gerar-pdf';

// Real pdfmake, no mocks: generation takes a few milliseconds.
describe('gerarPdf (DEC-019)', () => {
  it('generates a PDF with the standard font, accents included', async () => {
    const pdf = await gerarPdf({
      defaultStyle: { font: FONTE },
      content: [
        { text: 'Situação meteorológica', bold: true },
        { text: 'Ações em curso, alerta nº 10', italics: true },
      ],
    });

    expect(pdf.subarray(0, 5).toString()).toBe('%PDF-');
    expect(pdf.toString('latin1')).toContain('/BaseFont /Helvetica-Bold');
  });

  it('never reads local files', async () => {
    await expect(
      (async () =>
        gerarPdf({
          defaultStyle: { font: FONTE },
          content: [{ image: '/etc/hostname' }],
        }))(),
    ).rejects.toThrow('denied by resource access policy');
  });
});
