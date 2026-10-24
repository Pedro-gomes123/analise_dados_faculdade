import { ParametroAlertaHistorico } from '@/modules/alertas/entities/parametro-alerta-historico.entity';
import { ParametroAlerta } from '@/modules/alertas/entities/parametro-alerta.entity';
import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';

export class ParametroAlertaResponseDto {
  id!: number;
  variavel!: string;
  territorio!: string;
  limiar!: number;
  nivel!: string;
  ativo!: boolean;
  atualizado_em!: Date;

  static from(parametro: ParametroAlerta): ParametroAlertaResponseDto {
    return {
      id: parametro.id,
      variavel: parametro.variavel,
      territorio: parametro.territorio,
      limiar: parametro.limiar,
      nivel: parametro.nivel,
      ativo: parametro.ativo,
      atualizado_em: parametro.dthrAtualizacao,
    };
  }
}

// RN-001: who, when, before -> after.
export class ParametroAlertaHistoricoResponseDto {
  id!: number;
  operacao!: OperacaoHistorico;
  /** Nulo na criação */
  valor_anterior!: Record<string, unknown> | null;
  valor_novo!: Record<string, unknown>;
  autor!: { id: number; nome: string };
  registrado_em!: Date;

  static from(
    historico: ParametroAlertaHistorico,
  ): ParametroAlertaHistoricoResponseDto {
    return {
      id: historico.id,
      operacao: historico.operacao,
      valor_anterior: historico.valorAnterior,
      valor_novo: historico.valorNovo,
      autor: { id: historico.usuario.id, nome: historico.usuario.nome },
      registrado_em: historico.dthrCriacao,
    };
  }
}
