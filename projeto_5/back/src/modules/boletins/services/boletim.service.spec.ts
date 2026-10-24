import { MoreThanOrEqual, type Repository } from 'typeorm';
import { Usuario } from '@/modules/acesso/entities/usuario.entity';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';
import { BoletimService } from '@/modules/boletins/services/boletim.service';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';

const AGORA = new Date('2026-11-02T12:00:00.000Z');

const ACAO = Object.assign(new Acao(), {
  id: 7,
  descricao: 'Equipe enviada',
  idAlerta: 10,
  idUsuario: 2,
  usuario: Object.assign(new Usuario(), { id: 2, nome: 'Camila Rocha' }),
  dthrCriacao: new Date('2026-11-02T10:20:00Z'),
});

function setup() {
  const acoes = { find: jest.fn().mockResolvedValue([ACAO]) };
  const service = new BoletimService(acoes as unknown as Repository<Acao>);
  return { service, acoes };
}

describe('BoletimService (RN-009)', () => {
  it('reads the actions of the last 24 h, newest first (PR-022 b)', async () => {
    const { service, acoes } = setup();

    const documento = await service.montar([SecaoBoletim.AcoesAbrigos], AGORA);

    expect(acoes.find).toHaveBeenCalledWith({
      where: {
        dthrCriacao: MoreThanOrEqual(new Date('2026-11-01T12:00:00.000Z')),
      },
      relations: { usuario: true },
      order: { dthrCriacao: 'DESC', id: 'DESC' },
    });
    expect(documento.secoes[0].blocos[0]).toEqual({
      tipo: 'lista',
      itens: ['02/11/2026, 07:20: Equipe enviada (Camila Rocha, alerta nº 10)'],
    });
  });

  it('does not query actions when the section is not chosen', async () => {
    const { service, acoes } = setup();

    const documento = await service.montar(
      [SecaoBoletim.Rios, SecaoBoletim.Cabecalho],
      AGORA,
    );

    expect(acoes.find).not.toHaveBeenCalled();
    expect(documento.geradoEm).toBe(AGORA);
    expect(documento.secoes.map((s) => s.secao)).toEqual([
      SecaoBoletim.Cabecalho,
      SecaoBoletim.Rios,
    ]);
  });

  it('previews the same document as HTML (RN-009 #1)', async () => {
    const { service } = setup();

    const html = await service.preVisualizar(
      [SecaoBoletim.AcoesAbrigos, SecaoBoletim.Cabecalho],
      AGORA,
    );

    expect(html).toContain('<h1>Boletim de Emergência Climática</h1>');
    expect(html).toContain('Equipe enviada (Camila Rocha, alerta nº 10)');
    expect(html.indexOf('data-secao="cabecalho"')).toBeLessThan(
      html.indexOf('data-secao="acoes_abrigos"'),
    );
  });

  it('generates the PDF of the same document, named by date (RN-009 #4)', async () => {
    const { service, acoes } = setup();

    const pdf = await service.gerarPdf(
      [SecaoBoletim.AcoesAbrigos, SecaoBoletim.Cabecalho],
      AGORA,
    );

    expect(acoes.find).toHaveBeenCalledTimes(1);
    expect(pdf.nome).toBe('boletim-2026-11-02.pdf');
    expect(pdf.conteudo.subarray(0, 5).toString()).toBe('%PDF-');
  });
});
