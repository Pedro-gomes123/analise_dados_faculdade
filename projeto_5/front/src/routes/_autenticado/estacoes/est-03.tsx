import { createFileRoute } from '@tanstack/react-router'
import { PaginaDaEstacao } from '@/components/layout/PaginaDaEstacao'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-03')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GIN']),
  component: () => <PaginaDaEstacao papel="GIN" />,
})
