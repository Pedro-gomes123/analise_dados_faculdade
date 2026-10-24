import { createFileRoute } from '@tanstack/react-router'
import { PageTitle } from '@/components/PageTitle'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-01')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['TEC']),
  component: Pagina,
})

// Provisória: o conteúdo vem nas TASKs do REQ-008.
function Pagina() {
  return <PageTitle title="EST-01 · Técnico(a) Vigidesastres" />
}
