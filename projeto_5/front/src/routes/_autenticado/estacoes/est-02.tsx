import { createFileRoute } from '@tanstack/react-router'
import { PaginaDaEstacao } from '@/components/layout/PaginaDaEstacao'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-02')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GES']),
  component: () => <PaginaDaEstacao papel="GES" />,
})
