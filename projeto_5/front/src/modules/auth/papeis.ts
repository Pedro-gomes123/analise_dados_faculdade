import type { Papel } from '@/modules/auth/types'

// Nomes dos papéis (permissoes.md, PR-019), na ordem das estações.
export const PAPEIS: { valor: Papel; rotulo: string }[] = [
  { valor: 'TEC', rotulo: 'Técnico(a) Vigidesastres' },
  { valor: 'GES', rotulo: 'Gestor(a) de Emergências' },
  { valor: 'GIN', rotulo: 'Gestão Institucional' },
  { valor: 'COM', rotulo: 'Comunicação Institucional' },
  { valor: 'ADM', rotulo: 'Administrador' },
]
