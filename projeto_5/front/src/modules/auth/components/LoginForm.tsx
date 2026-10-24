import { useState, type FormEvent } from 'react'
import { ErrorAlert } from '@/components/ErrorAlert'
import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import { apiErrorMessage, apiErrorStatus } from '@/lib/http'
import { useLoginMutation } from '@/modules/auth/hooks/useAuth'
import type { Usuario } from '@/modules/auth/types'

interface LoginFormProps {
  onSuccess: (usuario: Usuario) => void
}

function mensagemDeErro(error: unknown): string {
  const status = apiErrorStatus(error)
  // FLX-001: mensagem única para e-mail inexistente, senha errada e usuário inativo.
  if (status === 401) return 'E-mail ou senha inválidos'
  if (status === 422) return apiErrorMessage(error) ?? 'Dados inválidos'
  if (status === undefined) return 'Não foi possível conectar ao servidor'
  return 'Erro inesperado. Tente de novo.'
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const loginMutation = useLoginMutation()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    loginMutation.mutate(
      { email: email.trim(), senha },
      { onSuccess: ({ usuario }) => onSuccess(usuario) },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      <FormField
        label="E-mail"
        type="email"
        autoComplete="username"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <FormField
        label="Senha"
        type="password"
        autoComplete="current-password"
        required
        value={senha}
        onChange={(e) => setSenha(e.target.value)}
      />

      {loginMutation.isError && <ErrorAlert>{mensagemDeErro(loginMutation.error)}</ErrorAlert>}

      <Button type="submit" disabled={loginMutation.isPending || !email || !senha}>
        {loginMutation.isPending ? 'Entrando...' : 'Entrar'}
      </Button>
    </form>
  )
}
