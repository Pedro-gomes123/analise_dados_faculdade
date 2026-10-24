import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { rotaInicial } from '@/modules/auth/estacoes'
import { carregarUsuario } from '@/modules/auth/guards'
import { LoginForm } from '@/modules/auth/components/LoginForm'
import { ApiStatus } from '@/modules/health/components/ApiStatus'

export const Route = createFileRoute('/login')({
  beforeLoad: async ({ context }) => {
    const usuario = await carregarUsuario(context.queryClient)
    const rota = usuario && rotaInicial(usuario.papeis)
    if (rota) throw redirect({ to: rota })
  },
  component: LoginPage,
})

function LoginPage() {
  const navigate = useNavigate()

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Sala de Situação</CardTitle>
          <CardDescription>Vigidesastres | Secretaria de Saúde do Recife</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm
            onSuccess={(usuario) => {
              const rota = rotaInicial(usuario.papeis)
              if (rota) void navigate({ to: rota })
            }}
          />
        </CardContent>
      </Card>
      <div className="text-sm">
        <ApiStatus />
      </div>
    </main>
  )
}
