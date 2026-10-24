import { useState } from 'react'
import { Paginacao } from '@/components/Paginacao'
import { QueryResult } from '@/components/QueryResult'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertasTable } from '@/modules/alertas/components/AlertasTable'
import { useAlertasQuery } from '@/modules/alertas/hooks/useAlertas'
import type { StatusAlerta } from '@/modules/alertas/types'

type FiltroStatus = StatusAlerta | 'TODOS'

// MOD-002 / PER-006: ativos por padrão; encerrados e todos formam o histórico.
export function AlertasPanel() {
  const [filtro, setFiltro] = useState<FiltroStatus>('ATIVO')
  const [page, setPage] = useState(1)
  const query = useAlertasQuery({ page, status: filtro === 'TODOS' ? undefined : filtro })

  return (
    <div className="grid gap-4">
      <Tabs
        value={filtro}
        onValueChange={(valor) => {
          setFiltro(valor as FiltroStatus)
          setPage(1)
        }}
      >
        <TabsList aria-label="Situação dos alertas">
          <TabsTrigger value="ATIVO">Ativos</TabsTrigger>
          <TabsTrigger value="ENCERRADO">Encerrados</TabsTrigger>
          <TabsTrigger value="TODOS">Todos</TabsTrigger>
        </TabsList>
      </Tabs>

      <QueryResult query={query}>
        {(pagina) => (
          <>
            <AlertasTable alertas={pagina.data} />
            <Paginacao
              page={pagina.meta.currentPage}
              totalPages={pagina.meta.totalPages}
              totalItems={pagina.meta.totalItems}
              onPageChange={setPage}
            />
          </>
        )}
      </QueryResult>
    </div>
  )
}
