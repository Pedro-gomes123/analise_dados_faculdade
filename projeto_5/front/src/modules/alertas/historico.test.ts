import { describe, expect, it } from 'vitest'
import { descreverMudancas } from '@/modules/alertas/historico'
import type { HistoricoParametro } from '@/modules/alertas/types'

const base: HistoricoParametro = {
  id: 1,
  operacao: 'ALTERACAO',
  valor_anterior: null,
  valor_novo: {},
  autor: { id: 1, nome: 'Camila' },
  registrado_em: '2026-10-24T13:00:00Z',
}

describe('descreverMudancas (RN-001)', () => {
  it('mostra antes → depois de cada campo alterado', () => {
    expect(
      descreverMudancas({
        ...base,
        valor_anterior: { limiar: 50, ativo: true },
        valor_novo: { limiar: 62.5, ativo: false },
      }),
    ).toEqual(['Limiar: 50 → 62,5', 'Situação: Ativo → Inativo'])
  })

  it('mostra só o valor novo na criação', () => {
    expect(
      descreverMudancas({
        ...base,
        operacao: 'CRIACAO',
        valor_novo: { variavel: 'chuva_1h', nivel: 'ALTO' },
      }),
    ).toEqual(['Variável: chuva_1h', 'Nível: ALTO'])
  })
})
