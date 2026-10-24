import { createFileRoute } from '@tanstack/react-router'
import { exigirPapel } from '@/modules/auth/guards'
import { Estacao04Page } from '@/modules/boletins/components/Estacao04Page'

export const Route = createFileRoute('/_autenticado/estacoes/est-04')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['COM']),
  component: Estacao04Page,
})
