import { createFileRoute, redirect } from '@tanstack/react-router'
import { rotaInicial } from '@/modules/auth/estacoes'
import { carregarUsuario } from '@/modules/auth/guards'

// Sem tela própria: manda para a estação do papel ou para o login (FLX-001).
export const Route = createFileRoute('/')({
  beforeLoad: async ({ context }) => {
    const usuario = await carregarUsuario(context.queryClient)
    throw redirect({ to: (usuario && rotaInicial(usuario.papeis)) || '/login' })
  },
})
