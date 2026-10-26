import { PageTitle } from '@/components/PageTitle'
import { itemDoPapel } from '@/components/layout/navegacao'
import type { Papel } from '@/modules/auth/types'

// Provisória: o conteúdo de cada estação vem nas TASKs do seu REQ (008 a 011).
export function PaginaDaEstacao({ papel }: { papel: Papel }) {
  const { codigo, titulo, descricao, icone } = itemDoPapel(papel)
  return <PageTitle icon={icone} title={`${codigo} · ${titulo}`} description={descricao} />
}
