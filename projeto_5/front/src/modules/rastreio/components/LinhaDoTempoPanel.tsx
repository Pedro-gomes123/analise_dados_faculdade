import { useState } from 'react'
import { PeriodoTabs } from '@/components/PeriodoTabs'
import { QueryResult } from '@/components/QueryResult'
import type { Periodo } from '@/lib/periodo'
import { LinhaDoTempoLista } from '@/modules/rastreio/components/LinhaDoTempoLista'
import { RegistrarAcaoForm } from '@/modules/rastreio/components/RegistrarAcaoForm'
import { useLinhaDoTempoQuery } from '@/modules/rastreio/hooks/useRastreio'

interface LinhaDoTempoPanelProps {
  /** PER-007: só o Gestor registra; GIN só acompanha até a DUV-036. */
  podeRegistrar: boolean
}

// REQ-006 / RN-005: até a DUV-030 definir "evento", a linha do tempo é por período.
export function LinhaDoTempoPanel({ podeRegistrar }: LinhaDoTempoPanelProps) {
  const [periodo, setPeriodo] = useState<Periodo>('24h')
  const query = useLinhaDoTempoQuery(periodo)

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="grid content-start gap-4">
        <PeriodoTabs value={periodo} onChange={setPeriodo} />
        <QueryResult query={query}>{(linha) => <LinhaDoTempoLista itens={linha.itens} />}</QueryResult>
      </div>
      {/* No celular o formulário vem antes da lista. */}
      {podeRegistrar && (
        <div className="order-first lg:order-none">
          <RegistrarAcaoForm />
        </div>
      )}
    </div>
  )
}
