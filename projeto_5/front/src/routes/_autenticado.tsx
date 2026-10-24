import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/react-router'
import { AppHeader } from '@/components/AppHeader'
import { carregarUsuario } from '@/modules/auth/guards'
import { useLogout, useUsuarioAtual } from '@/modules/auth/hooks/useAuth'

// Guarda de rotas (FLX-001): tudo abaixo daqui exige login.
export const Route = createFileRoute('/_autenticado')({
  beforeLoad: async ({ context }) => {
    const usuario = await carregarUsuario(context.queryClient)
    if (!usuario) throw redirect({ to: '/login' })
    return { usuario }
  },
  component: AutenticadoLayout,
})

function AutenticadoLayout() {
  const usuario = useUsuarioAtual()
  const logout = useLogout()
  const navigate = useNavigate()

  return (
    <>
      <AppHeader
        nome={usuario.nome}
        papeis={usuario.papeis}
        onLogout={() => {
          logout()
          void navigate({ to: '/login' })
        }}
      />
      <main className="p-6">
        <Outlet />
      </main>
    </>
  )
}
