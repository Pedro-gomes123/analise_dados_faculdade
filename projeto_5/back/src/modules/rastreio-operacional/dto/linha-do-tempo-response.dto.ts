import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { AcaoResponseDto } from '@/modules/rastreio-operacional/dto/acao-response.dto';

export class AlertaResumoDto {
  id!: number;
  variavel!: string;
  territorio!: string;
  nivel!: string;
  limiar!: number;
  valor_lido!: number;
  lida_em!: Date;
  status!: string;

  static from(alerta: Alerta): AlertaResumoDto {
    return {
      id: alerta.id,
      variavel: alerta.variavel,
      territorio: alerta.territorio,
      nivel: alerta.nivel,
      limiar: alerta.limiar,
      valor_lido: alerta.valorLido,
      lida_em: alerta.lidaEm,
      status: alerta.status,
    };
  }
}

// One timeline entry: `alerta` when tipo = ALERTA, `acao` when tipo = ACAO.
export class ItemLinhaDoTempoDto {
  tipo!: 'ALERTA' | 'ACAO';
  /** Disparo do alerta ou registro da ação */
  em!: Date;
  alerta?: AlertaResumoDto;
  acao?: AcaoResponseDto;
}

export class LinhaDoTempoResponseDto {
  inicio!: Date;
  fim!: Date;
  itens!: ItemLinhaDoTempoDto[];
}
