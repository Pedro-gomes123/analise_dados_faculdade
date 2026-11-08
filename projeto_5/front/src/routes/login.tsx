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
    <main className="flex min-h-screen items-center justify-center bg-muted/40 p-6">
      <div className="flex w-full max-w-sm flex-col gap-4">
      <Card>
        <CardHeader>
          <span className="mb-2 flex size-10 items-center justify-center rounded-md bg-primary text-lg font-bold text-primary-foreground">
            V
          </span>
          <CardTitle>O Vigia · Sala de Situação</CardTitle>
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
      </div>
    </main>
  )
}
