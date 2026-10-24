import { createFileRoute } from '@tanstack/react-router'
import { PageTitle } from '@/components/PageTitle'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/estacoes/est-04')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['COM']),
  component: Pagina,
})

// Provisória: o conteúdo vem nas TASKs do REQ-011.
function Pagina() {
  return <PageTitle title="EST-04 · Comunicação Institucional" />
}
