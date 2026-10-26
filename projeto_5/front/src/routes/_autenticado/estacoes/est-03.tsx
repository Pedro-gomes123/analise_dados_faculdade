import { createFileRoute } from '@tanstack/react-router'
import { exigirPapel } from '@/modules/auth/guards'
import { Estacao03Page } from '@/modules/indicadores/components/Estacao03Page'

export const Route = createFileRoute('/_autenticado/estacoes/est-03')({
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['GIN']),
  component: Estacao03Page,
})
