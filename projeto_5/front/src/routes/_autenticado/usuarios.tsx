import { createFileRoute } from '@tanstack/react-router'
import { PageTitle } from '@/components/PageTitle'
import { exigirPapel } from '@/modules/auth/guards'

export const Route = createFileRoute('/_autenticado/usuarios')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['ADM']),
  component: Pagina,
})

// Provisória: o conteúdo vem na TASK-019 (MOD-001).
function Pagina() {
  return <PageTitle title="Administração de usuários" />
}
