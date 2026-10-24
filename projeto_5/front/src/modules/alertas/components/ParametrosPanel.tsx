import { useState } from 'react'
import { History, Pencil, Plus } from 'lucide-react'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Paginacao } from '@/components/Paginacao'
import { QueryResult } from '@/components/QueryResult'
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
import { formatarDataHora, formatarNumero } from '@/lib/format'
import { describeApiError } from '@/lib/http'
import { HistoricoParametroDialog } from '@/modules/alertas/components/HistoricoParametroDialog'
import { ParametroFormDialog } from '@/modules/alertas/components/ParametroFormDialog'
import { useAlterarParametro, useParametrosQuery } from '@/modules/alertas/hooks/useAlertas'
import type { ParametroAlerta } from '@/modules/alertas/types'

interface ParametrosPanelProps {
  /** PER-005: só o Gestor altera; o Técnico consulta (PER-004). */
  podeEditar: boolean
}

export function ParametrosPanel({ podeEditar }: ParametrosPanelProps) {
  const [page, setPage] = useState(1)
  const [formAberto, setFormAberto] = useState(false)
  const [emEdicao, setEmEdicao] = useState<ParametroAlerta>()
  const [emHistorico, setEmHistorico] = useState<ParametroAlerta>()
  const [emAlternancia, setEmAlternancia] = useState<ParametroAlerta>()
  const query = useParametrosQuery(page)
  const alterar = useAlterarParametro()

  function abrirFormulario(parametro?: ParametroAlerta) {
    setEmEdicao(parametro)
    setFormAberto(true)
  }

  return (
    <div className="grid gap-4">
      {podeEditar && (
        <div className="flex justify-end">
          <Button onClick={() => abrirFormulario()}>
            <Plus />
            Novo parâmetro
          </Button>
        </div>
      )}

      <QueryResult query={query}>
        {(pagina) => (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Variável</TableHead>
                  <TableHead>Território</TableHead>
                  <TableHead className="text-right">Limiar</TableHead>
                  <TableHead>Nível</TableHead>
                  <TableHead>Situação</TableHead>
                  <TableHead>Atualizado em</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pagina.data.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      Nenhum parâmetro cadastrado.
                    </TableCell>
                  </TableRow>
                )}
                {pagina.data.map((parametro) => (
                  <TableRow key={parametro.id}>
                    <TableCell className="font-medium">{parametro.variavel}</TableCell>
                    <TableCell>{parametro.territorio}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatarNumero(parametro.limiar)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{parametro.nivel}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={parametro.ativo ? 'default' : 'outline'}>
                        {parametro.ativo ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatarDataHora(parametro.atualizado_em)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Histórico de ${parametro.variavel} em ${parametro.territorio}`}
                          onClick={() => setEmHistorico(parametro)}
                        >
                          <History />
                        </Button>
                        {podeEditar && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              aria-label={`Editar ${parametro.variavel} em ${parametro.territorio}`}
                              onClick={() => abrirFormulario(parametro)}
                            >
                              <Pencil />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                alterar.reset()
                                setEmAlternancia(parametro)
                              }}
                            >
                              {parametro.ativo ? 'Inativar' : 'Reativar'}
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Paginacao
              page={pagina.meta.currentPage}
              totalPages={pagina.meta.totalPages}
              totalItems={pagina.meta.totalItems}
              onPageChange={setPage}
            />
          </>
        )}
      </QueryResult>

      <ParametroFormDialog open={formAberto} onOpenChange={setFormAberto} parametro={emEdicao} />
      <HistoricoParametroDialog parametro={emHistorico} onClose={() => setEmHistorico(undefined)} />
      <ConfirmDialog
        open={!!emAlternancia}
        onOpenChange={(aberto) => !aberto && setEmAlternancia(undefined)}
        title={emAlternancia?.ativo ? 'Inativar parâmetro' : 'Reativar parâmetro'}
        description={
          emAlternancia?.ativo
            ? 'O parâmetro deixa de disparar alertas (RN-002). O histórico é mantido.'
            : 'O parâmetro volta a disparar alertas.'
        }
        confirmLabel={emAlternancia?.ativo ? 'Inativar' : 'Reativar'}
        destructive={emAlternancia?.ativo}
        pending={alterar.isPending}
        error={alterar.isError ? describeApiError(alterar.error) : undefined}
        onConfirm={() =>
          emAlternancia &&
          alterar.mutate(
            { id: emAlternancia.id, dados: { ativo: !emAlternancia.ativo } },
            { onSuccess: () => setEmAlternancia(undefined) },
          )
        }
      />
    </div>
  )
}
