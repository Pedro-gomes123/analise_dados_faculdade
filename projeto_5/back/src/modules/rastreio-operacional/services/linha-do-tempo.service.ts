import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Between, Repository } from 'typeorm';
import type { PeriodoQueryDto } from '@/core/dto/periodo-query.dto';
import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { montarLinhaDoTempo } from '@/modules/rastreio-operacional/domain/linha-do-tempo';
import { AcaoResponseDto } from '@/modules/rastreio-operacional/dto/acao-response.dto';
import {
  AlertaResumoDto,
  type LinhaDoTempoResponseDto,
} from '@/modules/rastreio-operacional/dto/linha-do-tempo-response.dto';
import { Acao } from '@/modules/rastreio-operacional/entities/acao.entity';

// RN-005 #2: until DUV-030 defines an "event", the timeline is a period.
@Injectable()
export class LinhaDoTempoService {
  constructor(
    @InjectRepository(Alerta) private readonly alertas: Repository<Alerta>,
    @InjectRepository(Acao) private readonly acoes: Repository<Acao>,
  ) {}

  async consultar(periodo: PeriodoQueryDto): Promise<LinhaDoTempoResponseDto> {
    const [alertas, acoes] = await Promise.all([
      this.alertas.find({
        where: { dthrDisparo: Between(periodo.inicio, periodo.fim) },
      }),
      this.acoes.find({
        where: { dthrCriacao: Between(periodo.inicio, periodo.fim) },
        relations: { usuario: true },
      }),
    ]);

    const itens = montarLinhaDoTempo(
      alertas.map((alerta) => ({
        em: alerta.dthrDisparo,
        alerta: AlertaResumoDto.from(alerta),
      })),
      acoes.map((acao) => ({
        em: acao.dthrCriacao,
        acao: AcaoResponseDto.from(acao),
      })),
    );

    return { inicio: periodo.inicio, fim: periodo.fim, itens };
  }
}
