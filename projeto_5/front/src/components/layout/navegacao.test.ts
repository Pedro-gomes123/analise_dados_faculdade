import { describe, expect, it } from 'vitest'
import { encontrarItemAtivo, secoesDoMenu } from '@/components/layout/navegacao'

describe('secoesDoMenu (DEC-021, REQ-013)', () => {
  it('separa estações e administração', () => {
    expect(
      secoesDoMenu(['ADM', 'GES']).map((s) => [s.titulo, s.itens.map((i) => i.codigo)]),
    ).toEqual([
      ['Estações', ['EST-02']],
      ['Administração', ['ADM']],
    ])
  })

  it('esconde a seção sem itens', () => {
    expect(secoesDoMenu(['COM']).map((s) => s.titulo)).toEqual(['Estações'])
    expect(secoesDoMenu(['ADM']).map((s) => s.titulo)).toEqual(['Administração'])
  })
})

describe('encontrarItemAtivo', () => {
  const secoes = secoesDoMenu(['TEC', 'ADM'])

  it('acha a seção e o item da página, inclusive com caminho interno', () => {
    expect(encontrarItemAtivo(secoes, '/estacoes/est-01')?.item.codigo).toBe('EST-01')
    expect(encontrarItemAtivo(secoes, '/usuarios/7')?.secao).toBe('Administração')
  })

  it('não confunde rotas com o mesmo prefixo', () => {
    expect(encontrarItemAtivo(secoes, '/usuarios-antigos')).toBeUndefined()
  })
})
