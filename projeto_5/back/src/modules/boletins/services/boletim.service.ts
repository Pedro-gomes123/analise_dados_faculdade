import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { MoreThanOrEqual, Repository } from 'typeorm';
import { FONTE, gerarPdf } from '@/infrastructure/pdf/gerar-pdf';
import {
  type AcaoBoletim,
  type DocumentoBoletim,
  JANELA_ACOES_MS,
  montarDocumentoBoletim,
} from '@/modules/boletins/domain/documento-boletim';
import { renderizarHtml } from '@/modules/boletins/domain/renderizar-html';
import {
  definicaoPdf,
  nomeDoArquivo,
} from '@/modules/boletins/domain/renderizar-pdf';
import { SecaoBoletim } from '@/modules/boletins/enums/secao-boletim.enum';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';

export interface ArquivoPdf {
  nome: string;
  conteudo: Buffer;
}

// RN-009. Gold sections (meteorologia, rios) arrive with TASK-032.
@Injectable()
export class BoletimService {
  constructor(
    @InjectRepository(Acao) private readonly acoes: Repository<Acao>,
  ) {}

  async montar(
    secoes: readonly SecaoBoletim[],
    agora = new Date(),
  ): Promise<DocumentoBoletim> {
    const acoes = secoes.includes(SecaoBoletim.AcoesAbrigos)
      ? await this.acoesEmCurso(agora)
      : [];
    return montarDocumentoBoletim(secoes, { geradoEm: agora, acoes });
  }

  async preVisualizar(
    secoes: readonly SecaoBoletim[],
    agora = new Date(),
  ): Promise<string> {
    return renderizarHtml(await this.montar(secoes, agora));
  }

  // RN-009 #4: same document as the preview.
  async gerarPdf(
    secoes: readonly SecaoBoletim[],
    agora = new Date(),
  ): Promise<ArquivoPdf> {
    const documento = await this.montar(secoes, agora);
    return {
      nome: nomeDoArquivo(documento.geradoEm),
      conteudo: await gerarPdf(definicaoPdf(documento, FONTE)),
    };
  }

  // PR-022 b: actions registered in the last 24 h, newest first.
  private async acoesEmCurso(agora: Date): Promise<AcaoBoletim[]> {
    const acoes = await this.acoes.find({
      where: {
        dthrCriacao: MoreThanOrEqual(
          new Date(agora.getTime() - JANELA_ACOES_MS),
        ),
      },
      relations: { usuario: true },
      order: { dthrCriacao: 'DESC', id: 'DESC' },
    });
    return acoes.map((acao) => ({
      descricao: acao.descricao,
      autor: acao.usuario.nome,
      registradaEm: acao.dthrCriacao,
      idAlerta: acao.idAlerta,
    }));
  }
}
