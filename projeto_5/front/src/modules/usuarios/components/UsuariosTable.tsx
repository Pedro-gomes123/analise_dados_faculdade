import { Pencil } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Usuario } from '@/modules/usuarios/types'

interface UsuariosTableProps {
  usuarios: Usuario[]
  onEditar: (usuario: Usuario) => void
  onAlternarAtivo: (usuario: Usuario) => void
}

export function UsuariosTable({ usuarios, onEditar, onAlternarAtivo }: UsuariosTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nome</TableHead>
          <TableHead>E-mail</TableHead>
          <TableHead>Papéis</TableHead>
          <TableHead>Situação</TableHead>
          <TableHead className="text-right">Ações</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {usuarios.length === 0 && (
          <TableRow>
            <TableCell colSpan={5} className="text-center text-muted-foreground">
              Nenhum usuário encontrado.
            </TableCell>
          </TableRow>
        )}
        {usuarios.map((usuario) => (
          <TableRow key={usuario.id}>
            <TableCell className="font-medium">{usuario.nome}</TableCell>
            <TableCell>{usuario.email}</TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {usuario.papeis.map((papel) => (
                  <Badge key={papel} variant="secondary">
                    {papel}
                  </Badge>
                ))}
              </div>
            </TableCell>
            <TableCell>
              <Badge variant={usuario.ativo ? 'default' : 'outline'}>
                {usuario.ativo ? 'Ativo' : 'Inativo'}
              </Badge>
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Editar ${usuario.nome}`}
                  onClick={() => onEditar(usuario)}
                >
                  <Pencil />
                </Button>
                <Button variant="outline" size="sm" onClick={() => onAlternarAtivo(usuario)}>
                  {usuario.ativo ? 'Inativar' : 'Reativar'}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
