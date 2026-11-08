import { OperacaoHistorico } from '@/modules/alertas/enums/operacao-historico.enum';

export interface CamposEditaveis {
  limiar: number;
  nivel: string;
  ativo: boolean;
}

export interface DiferencaParametro {
  operacao: OperacaoHistorico;
  anterior: Partial<CamposEditaveis>;
  novo: Partial<CamposEditaveis>;
}

const CAMPOS: (keyof CamposEditaveis)[] = ['limiar', 'nivel', 'ativo'];

// RN-001 #2: only the fields that actually change go to the history. Null when
// nothing changes, so a no-op PATCH leaves no history line.
export function diferencaParametro(
  atual: CamposEditaveis,
  dados: Partial<CamposEditaveis>,
): DiferencaParametro | null {
  const alterados = CAMPOS.filter(
    (campo) => dados[campo] !== undefined && dados[campo] !== atual[campo],
  );
  if (alterados.length === 0) return null;

  const anterior: Partial<CamposEditaveis> = {};
  const novo: Partial<CamposEditaveis> = {};
  for (const campo of alterados) {
    Object.assign(anterior, { [campo]: atual[campo] });
    Object.assign(novo, { [campo]: dados[campo] });
  }

  // RN-001 #3: deactivation is its own operation, even with other fields.
  const operacao =
    novo.ativo === false
      ? OperacaoHistorico.Inativacao
      : OperacaoHistorico.Alteracao;
  return { operacao, anterior, novo };
}
