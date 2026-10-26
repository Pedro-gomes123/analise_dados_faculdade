import { Alerta } from '@/modules/alertas/entities/alerta.entity';
import { StatusAlerta } from '@/modules/alertas/enums/status-alerta.enum';

class ParametroResumoDto {
  id!: number;
  variavel!: string;
  limiar!: number;
}

// API shape of an alert (MOD-002 contract, DEC-011). Parameter fields are the
// copy taken at trigger time, not the parameter's current values.
export class AlertaResponseDto {
  id!: number;
  nivel!: string;
  parametro!: ParametroResumoDto;
  territorio!: string;
  valor_lido!: number;
  fonte!: string;
  lida_em!: Date;
  disparado_em!: Date;
  /** Última atualização da fonte (RN-007); nula enquanto o contrato do gold não existe (DEC-009) */
  fonte_atualizada_em!: Date | null;
  status!: StatusAlerta;

  static from(alerta: Alerta): AlertaResponseDto {
    return {
      id: alerta.id,
      nivel: alerta.nivel,
      parametro: {
        id: alerta.idParametroAlerta,
        variavel: alerta.variavel,
        limiar: alerta.limiar,
      },
      territorio: alerta.territorio,
      valor_lido: alerta.valorLido,
      fonte: alerta.fonte,
      lida_em: alerta.lidaEm,
      disparado_em: alerta.dthrDisparo,
      // RN-007 #2: never the current time when the source date is unknown.
      fonte_atualizada_em: null,
      status: alerta.status,
    };
  }
}
