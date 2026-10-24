import { createFileRoute } from '@tanstack/react-router'
import { PageTitle } from '@/components/PageTitle'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-02')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GES']),
  component: Pagina,
})

// Provisória: o conteúdo vem nas TASKs do REQ-009.
function Pagina() {
  return <PageTitle title="EST-02 · Gestor(a) de Emergências" />
}
