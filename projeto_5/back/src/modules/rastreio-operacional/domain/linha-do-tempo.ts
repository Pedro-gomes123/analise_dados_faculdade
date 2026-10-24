// RN-005: alerts triggered and actions registered, in chronological order.

export type ItemLinhaDoTempo<A, C> =
  { tipo: 'ALERTA'; em: Date; alerta: A } | { tipo: 'ACAO'; em: Date; acao: C };

// Same instant: the alert comes first, since an action responds to an alert.
const ORDEM_NO_EMPATE = { ALERTA: 0, ACAO: 1 } as const;

export function montarLinhaDoTempo<A, C>(
  alertas: { em: Date; alerta: A }[],
  acoes: { em: Date; acao: C }[],
): ItemLinhaDoTempo<A, C>[] {
  const itens: ItemLinhaDoTempo<A, C>[] = [
    ...alertas.map((a) => ({ tipo: 'ALERTA' as const, ...a })),
    ...acoes.map((a) => ({ tipo: 'ACAO' as const, ...a })),
  ];
  return itens.sort(
    (x, y) =>
      x.em.getTime() - y.em.getTime() ||
      ORDEM_NO_EMPATE[x.tipo] - ORDEM_NO_EMPATE[y.tipo],
  );
}
