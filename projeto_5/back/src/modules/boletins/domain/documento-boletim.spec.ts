import {
  type AcaoBoletim,
  montarDocumentoBoletim,
  ordenarSecoes,
} from '@/modules/boletins/domain/documento-boletim';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';

const GERADO_EM = new Date('2026-11-02T12:00:00Z');

const ACAO: AcaoBoletim = {
  descricao: 'Equipe enviada',
  autor: 'Camila Rocha',
  registradaEm: new Date('2026-11-02T10:20:00Z'),
  idAlerta: 10,
};

const montar = (secoes: SecaoBoletim[], acoes: AcaoBoletim[] = []) =>
  montarDocumentoBoletim(secoes, { geradoEm: GERADO_EM, acoes });

const secao = (secoes: SecaoBoletim[], acoes: AcaoBoletim[] = []) =>
  montar(secoes, acoes).secoes[0];

describe('ordenarSecoes (RN-009 #1, PR-022 d)', () => {
  it('puts the sections in the RN-009 order', () => {
    expect(
      ordenarSecoes([
        SecaoBoletim.Contatos,
        SecaoBoletim.Cabecalho,
        SecaoBoletim.Rios,
      ]),
    ).toEqual([
      SecaoBoletim.Cabecalho,
      SecaoBoletim.Rios,
      SecaoBoletim.Contatos,
    ]);
  });

  it('keeps a repeated section once', () => {
    expect(ordenarSecoes([SecaoBoletim.Rios, SecaoBoletim.Rios])).toEqual([
      SecaoBoletim.Rios,
    ]);
  });
});

describe('montarDocumentoBoletim (RN-009, PR-022)', () => {
  it('has only the chosen sections, with their titles', () => {
    const documento = montar([
      SecaoBoletim.AcoesAbrigos,
      SecaoBoletim.Meteorologia,
    ]);

    expect(documento.geradoEm).toBe(GERADO_EM);
    expect(documento.secoes.map((s) => [s.secao, s.titulo])).toEqual([
      [SecaoBoletim.Meteorologia, 'Situação meteorológica'],
      [SecaoBoletim.AcoesAbrigos, 'Ações em curso e abrigos'],
    ]);
  });

  it('header: institution and generation time in Recife (PR-022 a)', () => {
    expect(secao([SecaoBoletim.Cabecalho])).toEqual({
      secao: SecaoBoletim.Cabecalho,
      titulo: 'Boletim de Emergência Climática',
      blocos: [
        {
          tipo: 'paragrafo',
          texto: 'Secretaria Executiva de Vigilância em Saúde do Recife',
        },
        { tipo: 'paragrafo', texto: 'Gerado em 02/11/2026, 09:00' },
      ],
    });
  });

  it('actions: one line per action, with author and linked alert (PR-022 b)', () => {
    const semAlerta = {
      ...ACAO,
      descricao: 'Abrigo vistoriado',
      idAlerta: null,
    };

    expect(
      secao([SecaoBoletim.AcoesAbrigos], [ACAO, semAlerta]).blocos,
    ).toEqual([
      {
        tipo: 'lista',
        itens: [
          '02/11/2026, 07:20: Equipe enviada (Camila Rocha, alerta nº 10)',
          '02/11/2026, 07:20: Abrigo vistoriado (Camila Rocha)',
        ],
      },
      {
        tipo: 'aviso',
        texto: 'Informações de abrigos ainda não estão disponíveis no sistema.',
      },
    ]);
  });

  it('actions: says so when there is none', () => {
    expect(secao([SecaoBoletim.AcoesAbrigos]).blocos[0]).toEqual({
      tipo: 'paragrafo',
      texto: 'Nenhuma ação registrada nas últimas 24 horas.',
    });
  });

  it.each([SecaoBoletim.Meteorologia, SecaoBoletim.Rios])(
    '%s: unavailable until the gold contract (PR-022 c)',
    (escolhida) => {
      expect(secao([escolhida]).blocos).toEqual([
        {
          tipo: 'aviso',
          texto:
            'Conteúdo indisponível: estes dados ainda não estão integrados ao sistema.',
        },
      ]);
    },
  );

  it.each([SecaoBoletim.RiscosSaude, SecaoBoletim.Contatos])(
    '%s: unavailable until DUV-033 (PR-022 c)',
    (escolhida) => {
      expect(secao([escolhida]).blocos).toEqual([
        {
          tipo: 'aviso',
          texto:
            'Conteúdo indisponível: a origem deste conteúdo ainda não foi definida.',
        },
      ]);
    },
  );
});
