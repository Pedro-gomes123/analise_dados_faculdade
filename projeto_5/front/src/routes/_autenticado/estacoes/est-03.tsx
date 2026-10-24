import { createFileRoute } from '@tanstack/react-router'
import { PageTitle } from '@/components/PageTitle'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-03')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GIN']),
  component: Pagina,
})

// Provisória: o conteúdo vem nas TASKs do REQ-010.
function Pagina() {
  return <PageTitle title="EST-03 · Gestão Institucional" />
}
