import { useState, type FormEvent } from 'react'
import { Plus, Search, Users } from 'lucide-react'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { PageTitle } from '@/components/PageTitle'
import { Paginacao } from '@/components/Paginacao'
import { QueryResult } from '@/components/QueryResult'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { describeApiError } from '@/lib/http'
import { UsuarioFormDialog } from '@/modules/usuarios/components/UsuarioFormDialog'
import { UsuariosTable } from '@/modules/usuarios/components/UsuariosTable'
import { useAlterarUsuario, useUsuariosQuery } from '@/modules/usuarios/hooks/useUsuarios'
import type { Usuario } from '@/modules/usuarios/types'

interface UsuariosPageProps {
  page: number
  busca: string
  onSearchChange: (search: { page: number; busca: string }) => void
}

// MOD-001 / PER-003: listar, criar, editar e inativar usuários.
export function UsuariosPage({ page, busca, onSearchChange }: UsuariosPageProps) {
  const [termo, setTermo] = useState(busca)
  const [formAberto, setFormAberto] = useState(false)
  const [emEdicao, setEmEdicao] = useState<Usuario>()
  const [emAlternancia, setEmAlternancia] = useState<Usuario>()
  const usuariosQuery = useUsuariosQuery({ page, busca })
  const alterar = useAlterarUsuario()

  function buscar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearchChange({ page: 1, busca: termo.trim() })
  }

  function abrirFormulario(usuario?: Usuario) {
    setEmEdicao(usuario)
    setFormAberto(true)
  }

  function abrirAlternancia(usuario: Usuario) {
    alterar.reset()
    setEmAlternancia(usuario)
  }

  function confirmarAlternancia() {
    if (!emAlternancia) return
    alterar.mutate(
      { id: emAlternancia.id, dados: { ativo: !emAlternancia.ativo } },
      { onSuccess: () => setEmAlternancia(undefined) },
    )
  }

  return (
    <>
      <PageTitle
        icon={Users}
        title="Usuários"
        description="Contas, papéis e acesso ao sistema (PER-003)"
      >
        <Button onClick={() => abrirFormulario()}>
          <Plus />
          Novo usuário
        </Button>
      </PageTitle>

      <Card>
        <CardContent className="grid gap-4">
          <form onSubmit={buscar} role="search" className="flex gap-2">
            <Input
              aria-label="Buscar por nome ou e-mail"
              placeholder="Buscar por nome ou e-mail"
              value={termo}
              onChange={(e) => setTermo(e.target.value)}
              className="max-w-sm"
            />
            <Button type="submit" variant="outline">
              <Search />
              Buscar
            </Button>
          </form>

          <QueryResult query={usuariosQuery}>
            {(pagina) => (
              <>
                <UsuariosTable
                  usuarios={pagina.data}
                  onEditar={abrirFormulario}
                  onAlternarAtivo={abrirAlternancia}
                />
                <Paginacao
                  page={pagina.meta.currentPage}
                  totalPages={pagina.meta.totalPages}
                  totalItems={pagina.meta.totalItems}
                  onPageChange={(novaPagina) => onSearchChange({ page: novaPagina, busca })}
                />
              </>
            )}
          </QueryResult>
        </CardContent>
      </Card>

      <UsuarioFormDialog open={formAberto} onOpenChange={setFormAberto} usuario={emEdicao} />

      <ConfirmDialog
        open={!!emAlternancia}
        onOpenChange={(aberto) => !aberto && setEmAlternancia(undefined)}
        title={emAlternancia?.ativo ? 'Inativar usuário' : 'Reativar usuário'}
        description={
          emAlternancia?.ativo
            ? `${emAlternancia.nome} não poderá mais entrar no sistema. O histórico é mantido.`
            : `${emAlternancia?.nome ?? ''} poderá entrar no sistema de novo.`
        }
        confirmLabel={emAlternancia?.ativo ? 'Inativar' : 'Reativar'}
        destructive={emAlternancia?.ativo}
        pending={alterar.isPending}
        error={alterar.isError ? describeApiError(alterar.error) : undefined}
        onConfirm={confirmarAlternancia}
      />
    </>
  )
}
