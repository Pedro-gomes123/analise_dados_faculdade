import { createFileRoute } from '@tanstack/react-router'
import { exigirPapel } from '@/modules/auth/guards'
import { UsuariosPage } from '@/modules/usuarios/components/UsuariosPage'

interface UsuariosSearch {
  page?: number
  busca?: string
}

export const Route = createFileRoute('/_autenticado/usuarios')({
  validateSearch: (search: Record<string, unknown>): UsuariosSearch => {
    const page = Number(search.page)
    return {
      page: Number.isInteger(page) && page > 1 ? page : undefined,
      busca: typeof search.busca === 'string' && search.busca ? search.busca : undefined,
    }
  },
  beforeLoad: ({ context }) => exigirPapel(context.usuario, ['ADM']),
  component: Pagina,
})

function Pagina() {
  const { page = 1, busca = '' } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <UsuariosPage
      page={page}
      busca={busca}
      onSearchChange={(search) =>
        void navigate({
          search: { page: search.page > 1 ? search.page : undefined, busca: search.busca || undefined },
        })
      }
    />
  )
}
