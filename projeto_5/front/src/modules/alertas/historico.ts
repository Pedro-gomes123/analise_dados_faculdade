import { formatarNumero } from '@/lib/format'
import type { HistoricoParametro, OperacaoHistorico } from '@/modules/alertas/types'

export const ROTULO_OPERACAO: Record<OperacaoHistorico, string> = {
  CRIACAO: 'Criação',
  ALTERACAO: 'Alteração',
  INATIVACAO: 'Inativação',
}

const ROTULO_CAMPO: Record<string, string> = {
  variavel: 'Variável',
  territorio: 'Território',
  limiar: 'Limiar',
  nivel: 'Nível',
  ativo: 'Situação',
}

function formatarValor(valor: unknown): string {
  if (valor === undefined || valor === null) return '—'
  if (typeof valor === 'boolean') return valor ? 'Ativo' : 'Inativo'
  if (typeof valor === 'number') return formatarNumero(valor)
  return String(valor)
}

// RN-001: "Limiar: 50 → 60" por campo; na criação, só o valor novo.
export function descreverMudancas({ valor_anterior, valor_novo }: HistoricoParametro): string[] {
  return Object.entries(valor_novo).map(([campo, novo]) => {
    const rotulo = ROTULO_CAMPO[campo] ?? campo
    if (!valor_anterior) return `${rotulo}: ${formatarValor(novo)}`
    return `${rotulo}: ${formatarValor(valor_anterior[campo])} → ${formatarValor(novo)}`
  })
}
