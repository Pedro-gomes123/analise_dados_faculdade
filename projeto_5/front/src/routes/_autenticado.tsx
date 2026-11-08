import { createFileRoute, Outlet, redirect, useNavigate, useRouterState } from '@tanstack/react-router'
import { Cabecalho } from '@/components/layout/Cabecalho'
import { MenuLateral } from '@/components/layout/MenuLateral'
import { MenuMovel } from '@/components/layout/MenuMovel'
import { encontrarItemAtivo, secoesDoMenu } from '@/components/layout/navegacao'
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

// Menu lateral à esquerda e a página num painel com a trilha no topo (DEC-021).
function AutenticadoLayout() {
  const usuario = useUsuarioAtual()
  const logout = useLogout()
  const navigate = useNavigate()
  const caminhoAtual = useRouterState({ select: (estado) => estado.location.pathname })

  const secoes = secoesDoMenu(usuario.papeis)
  const ativo = encontrarItemAtivo(secoes, caminhoAtual)
  const menu = {
    secoes,
    nome: usuario.nome,
    papeis: usuario.papeis,
    onLogout: () => {
      logout()
      void navigate({ to: '/login' })
    },
  }

  return (
    <div className="flex min-h-screen bg-muted/40 text-foreground">
      <MenuLateral {...menu} />
      <div className="flex min-w-0 flex-1 flex-col p-2 md:pl-0">
        <div className="flex flex-1 flex-col rounded-xl border bg-background">
          <Cabecalho
            menu={<MenuMovel {...menu} />}
            trilha={ativo && { secao: ativo.secao, pagina: ativo.item.titulo }}
          />
          <main className="flex-1 p-4 md:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
