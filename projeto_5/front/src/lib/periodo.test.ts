import { describe, expect, it } from 'vitest'
import { intervaloDoPeriodo } from '@/lib/periodo'

const AGORA = new Date('2026-10-24T13:00:00.000Z')

describe('intervaloDoPeriodo (PR-018)', () => {
  it.each([
    ['24h', '2026-10-23T13:00:00.000Z'],
    ['7d', '2026-10-17T13:00:00.000Z'],
    ['30d', '2026-09-24T13:00:00.000Z'],
  ] as const)('%s termina agora', (periodo, inicio) => {
    expect(intervaloDoPeriodo(periodo, AGORA)).toEqual({ inicio, fim: AGORA.toISOString() })
  })
})
