import { describe, expect, it } from 'vitest'
import { rotaInicial, temPapel } from '@/modules/auth/estacoes'

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
})
