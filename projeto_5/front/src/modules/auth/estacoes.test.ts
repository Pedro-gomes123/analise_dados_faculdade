import { describe, expect, it } from 'vitest'
import { estacoesDoUsuario, rotaInicial, temPapel } from '@/modules/auth/estacoes'

describe('rotaInicial', () => {
  it.each([
    [['TEC'], '/estacoes/est-01'],
    [['GES'], '/estacoes/est-02'],
    [['GIN'], '/estacoes/est-03'],
    [['COM'], '/estacoes/est-04'],
    [['ADM'], '/usuarios'],
  ] as const)('abre a estação do papel %j', (papeis, rota) => {
    expect(rotaInicial([...papeis])).toBe(rota)
  })

  it('usa a ordem das estações, não a ordem alfabética do back', () => {
    expect(rotaInicial(['ADM', 'COM', 'GES'])).toBe('/estacoes/est-02')
  })

  it('devolve null sem papel', () => {
    expect(rotaInicial([])).toBeNull()
  })
})

describe('temPapel', () => {
  it('vale a união dos papéis (AM-004 c)', () => {
    expect(temPapel(['COM', 'TEC'], ['TEC'])).toBe(true)
    expect(temPapel(['COM'], ['TEC', 'GES'])).toBe(false)
  })

  it('o ADM passa em qualquer estação (PR-023)', () => {
    expect(temPapel(['ADM'], ['COM'])).toBe(true)
    expect(temPapel(['ADM'], ['GES', 'GIN'])).toBe(true)
  })
})

describe('estacoesDoUsuario (REQ-013)', () => {
  it('mostra só as estações dos papéis do usuário, na ordem EST-01 a EST-04', () => {
    expect(estacoesDoUsuario(['COM', 'TEC']).map((e) => e.codigo)).toEqual(['EST-01', 'EST-04'])
  })

  it('o ADM vê as quatro estações e a administração (PR-023)', () => {
    expect(estacoesDoUsuario(['ADM']).map((e) => e.codigo)).toEqual([
      'EST-01',
      'EST-02',
      'EST-03',
      'EST-04',
      'ADM',
    ])
  })

  it('usa o nome da estação (EQP-14)', () => {
    expect(estacoesDoUsuario(['GES'])).toEqual([
      {
        papel: 'GES',
        codigo: 'EST-02',
        titulo: 'Gestor(a) de Emergências',
        descricao: 'Mapa de risco, alertas automáticos por parâmetro e linha do tempo do evento',
        rota: '/estacoes/est-02',
      },
    ])
  })
})
