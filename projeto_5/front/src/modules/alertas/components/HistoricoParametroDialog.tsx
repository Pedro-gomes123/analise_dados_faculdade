import { useState } from 'react'
import { Paginacao } from '@/components/Paginacao'
import { QueryResult } from '@/components/QueryResult'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { formatarDataHora } from '@/lib/format'
import { descreverMudancas, ROTULO_OPERACAO } from '@/modules/alertas/historico'
import { useHistoricoQuery } from '@/modules/alertas/hooks/useAlertas'
import type { ParametroAlerta } from '@/modules/alertas/types'

interface HistoricoParametroDialogProps {
  parametro?: ParametroAlerta
  onClose: () => void
}

export function HistoricoParametroDialog({ parametro, onClose }: HistoricoParametroDialogProps) {
  return (
    <Dialog open={!!parametro} onOpenChange={(aberto) => !aberto && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Histórico do parâmetro</DialogTitle>
          <DialogDescription>
            {parametro && `${parametro.variavel} · ${parametro.territorio}`}
          </DialogDescription>
        </DialogHeader>
        {parametro && <ListaDoHistorico id={parametro.id} />}
      </DialogContent>
    </Dialog>
  )
}

function ListaDoHistorico({ id }: { id: number }) {
  const [page, setPage] = useState(1)
  const query = useHistoricoQuery(id, page)

  return (
    <QueryResult query={query}>
      {(pagina) => (
        <div className="grid gap-4">
          <ol className="grid max-h-96 gap-3 overflow-y-auto">
            {pagina.data.map((item) => (
              <li key={item.id} className="rounded-lg border p-3 text-sm">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <Badge variant="secondary">{ROTULO_OPERACAO[item.operacao]}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {item.autor.nome} · {formatarDataHora(item.registrado_em)}
                  </span>
                </div>
                <ul className="text-muted-foreground">
                  {descreverMudancas(item).map((linha) => (
                    <li key={linha}>{linha}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          <Paginacao
            page={pagina.meta.currentPage}
            totalPages={pagina.meta.totalPages}
            totalItems={pagina.meta.totalItems}
            onPageChange={setPage}
          />
        </div>
      )}
    </QueryResult>
  )
}
