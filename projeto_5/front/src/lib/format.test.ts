import { describe, expect, it } from 'vitest'
import { formatarDataHora, formatarNumero, lerNumero } from '@/lib/format'

describe('format', () => {
  it('mostra a data UTC no horário do Recife (UTC−3)', () => {
    expect(formatarDataHora('2026-10-24T13:05:00Z')).toBe('24/10/2026 10:05')
  })

  it('usa vírgula decimal e até 3 casas', () => {
    expect(formatarNumero(1234.5)).toBe('1.234,5')
    expect(formatarNumero(62.1234)).toBe('62,123')
  })
})

describe('lerNumero', () => {
  it.each([
    ['62,5', 62.5],
    ['1.234,5', 1234.5],
    ['-3', -3],
    [' 50 ', 50],
  ])('lê %j', (texto, valor) => {
    expect(lerNumero(texto)).toBe(valor)
  })

  it.each(['', 'abc', '1,2,3', '12a'])('recusa %j', (texto) => {
    expect(lerNumero(texto)).toBeNull()
  })
})
