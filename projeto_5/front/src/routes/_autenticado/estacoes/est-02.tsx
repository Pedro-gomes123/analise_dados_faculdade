import { createFileRoute } from '@tanstack/react-router'
import { exigirPapel } from '@/modules/auth/guards'
import { Estacao02Page } from '@/modules/alertas/components/Estacao02Page'

export const Route = createFileRoute('/_autenticado/estacoes/est-02')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GES']),
  component: Estacao02Page,
})
