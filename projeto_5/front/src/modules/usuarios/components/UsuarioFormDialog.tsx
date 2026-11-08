import { useState, type FormEvent } from 'react'
import { CheckboxGroup } from '@/components/CheckboxGroup'
import { ErrorAlert } from '@/components/ErrorAlert'
import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { describeApiError } from '@/lib/http'
import { PAPEIS } from '@/modules/auth/papeis'
import type { Papel } from '@/modules/auth/types'
import { useAlterarUsuario, useCriarUsuario } from '@/modules/usuarios/hooks/useUsuarios'
import type { AlterarUsuarioRequest, Usuario } from '@/modules/usuarios/types'

// Mesmo limite do back (PR-020).
const SENHA_MIN = 8

interface UsuarioFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Sem usuário: cadastro. Com usuário: edição. */
  usuario?: Usuario
}

export function UsuarioFormDialog({ open, onOpenChange, usuario }: UsuarioFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{usuario ? 'Editar usuário' : 'Novo usuário'}</DialogTitle>
        </DialogHeader>
        {/* key: o formulário recomeça a cada abertura. */}
        {open && (
          <UsuarioForm
            key={usuario?.id ?? 'novo'}
            usuario={usuario}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

interface UsuarioFormProps {
  usuario?: Usuario
  onDone: () => void
}

function UsuarioForm({ usuario, onDone }: UsuarioFormProps) {
  const [nome, setNome] = useState(usuario?.nome ?? '')
  const [email, setEmail] = useState(usuario?.email ?? '')
  const [senha, setSenha] = useState('')
  const [papeis, setPapeis] = useState<Papel[]>(usuario?.papeis ?? [])
  const criar = useCriarUsuario()
  const alterar = useAlterarUsuario()
  const mutation = usuario ? alterar : criar

  const senhaObrigatoria = !usuario
  const senhaCurta = senha.length > 0 && senha.length < SENHA_MIN
  const podeSalvar =
    nome.trim() !== '' &&
    email.trim() !== '' &&
    papeis.length > 0 &&
    !senhaCurta &&
    (!senhaObrigatoria || senha !== '') &&
    !mutation.isPending

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!usuario) {
      criar.mutate({ nome: nome.trim(), email: email.trim(), senha, papeis }, { onSuccess: onDone })
      return
    }
    const dados: AlterarUsuarioRequest = { nome: nome.trim(), papeis }
    if (senha) dados.senha = senha
    alterar.mutate({ id: usuario.id, dados }, { onSuccess: onDone })
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      <FormField label="Nome" required value={nome} onChange={(e) => setNome(e.target.value)} />
      <FormField
        label="E-mail"
        type="email"
        required
        disabled={!!usuario}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <FormField
        label={usuario ? 'Nova senha (deixe em branco para manter)' : 'Senha inicial'}
        type="password"
        autoComplete="new-password"
        required={senhaObrigatoria}
        aria-invalid={senhaCurta}
        value={senha}
        onChange={(e) => setSenha(e.target.value)}
      />
      {senhaCurta && (
        <p className="-mt-2 text-sm text-destructive">
          A senha precisa ter ao menos {SENHA_MIN} caracteres
        </p>
      )}
      <CheckboxGroup legend="Papéis" options={PAPEIS} value={papeis} onChange={setPapeis} />

      {mutation.isError && <ErrorAlert>{describeApiError(mutation.error)}</ErrorAlert>}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" disabled={!podeSalvar}>
          {mutation.isPending ? 'Salvando...' : 'Salvar'}
        </Button>
      </DialogFooter>
    </form>
  )
}
