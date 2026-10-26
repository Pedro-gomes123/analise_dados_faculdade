import {
  Activity,
  ChartColumn,
  Megaphone,
  Siren,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { estacoesDoUsuario, type Estacao } from '@/modules/auth/estacoes'
import type { Papel } from '@/modules/auth/types'

export interface ItemDoMenu extends Estacao {
  icone: LucideIcon
}

export interface SecaoDoMenu {
  titulo: string
  itens: ItemDoMenu[]
}

const ICONE_POR_PAPEL: Record<Papel, LucideIcon> = {
  TEC: Activity,
  GES: Siren,
  GIN: ChartColumn,
  COM: Megaphone,
  ADM: Users,
}

// Menu lateral (DEC-021): só as estações dos papéis do usuário (REQ-013).
export function secoesDoMenu(papeis: Papel[]): SecaoDoMenu[] {
  const itens = estacoesDoUsuario(papeis).map((estacao) => ({
    ...estacao,
    icone: ICONE_POR_PAPEL[estacao.papel],
  }))
  const secoes: SecaoDoMenu[] = [
    { titulo: 'Estações', itens: itens.filter((i) => i.papel !== 'ADM') },
    { titulo: 'Administração', itens: itens.filter((i) => i.papel === 'ADM') },
  ]
  return secoes.filter((secao) => secao.itens.length > 0)
}

export function itemDoPapel(papel: Papel): ItemDoMenu {
  const [estacao] = estacoesDoUsuario([papel])
  return { ...estacao!, icone: ICONE_POR_PAPEL[papel] }
}

// Seção e item da página aberta, para a trilha do cabeçalho.
export function encontrarItemAtivo(
  secoes: SecaoDoMenu[],
  caminhoAtual: string,
): { secao: string; item: ItemDoMenu } | undefined {
  for (const secao of secoes) {
    const item = secao.itens.find(
      ({ rota }) => caminhoAtual === rota || caminhoAtual.startsWith(`${rota}/`),
    )
    if (item) return { secao: secao.titulo, item }
  }
  return undefined
}
