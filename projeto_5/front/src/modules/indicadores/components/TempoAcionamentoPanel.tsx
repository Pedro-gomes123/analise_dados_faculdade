import { useState } from 'react'
import { CircleAlert, CircleCheck, Timer } from 'lucide-react'
import { PeriodoTabs } from '@/components/PeriodoTabs'
import { QueryResult } from '@/components/QueryResult'
import { StatCard } from '@/components/StatCard'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatarDataHora, formatarDuracao } from '@/lib/format'
import type { Periodo } from '@/lib/periodo'
import { useTempoAcionamentoQuery } from '@/modules/indicadores/hooks/useIndicadores'
import type { TempoAcionamento } from '@/modules/indicadores/types'

// REQ-018 / RN-006: tempo entre o alerta e a primeira ação, por alerta e a média.
export function TempoAcionamentoPanel() {
  const [periodo, setPeriodo] = useState<Periodo>('7d')
  const query = useTempoAcionamentoQuery(periodo)

  return (
    <div className="grid gap-4">
      <PeriodoTabs value={periodo} onChange={setPeriodo} />
      <QueryResult query={query}>{(dados) => <Resumo dados={dados} />}</QueryResult>
    </div>
  )
}

function Resumo({ dados }: { dados: TempoAcionamento }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={Timer}
          label="Tempo médio de acionamento"
          value={dados.media_segundos === null ? '—' : formatarDuracao(dados.media_segundos)}
          hint="Do disparo do alerta até a primeira ação ligada"
        />
        <StatCard
          icon={CircleCheck}
          label="Alertas com ação"
          value={String(dados.alertas_com_acao)}
          hint="Entram na média"
        />
        {/* PR-021: alerta sem ação fica fora da média e aparece à parte. */}
        <StatCard
          icon={CircleAlert}
          label="Alertas sem ação"
          value={String(dados.alertas_sem_acao)}
          hint="Fora da média"
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Disparado em</TableHead>
            <TableHead>Nível</TableHead>
            <TableHead>Variável</TableHead>
            <TableHead>Território</TableHead>
            <TableHead>Primeira ação</TableHead>
            <TableHead className="text-right">Tempo</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dados.alertas.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground">
                Nenhum alerta no período.
              </TableCell>
            </TableRow>
          )}
          {dados.alertas.map((alerta) => (
            <TableRow key={alerta.id}>
              <TableCell>{formatarDataHora(alerta.disparado_em)}</TableCell>
              <TableCell>
                <Badge variant="secondary">{alerta.nivel}</Badge>
              </TableCell>
              <TableCell>{alerta.variavel}</TableCell>
              <TableCell>{alerta.territorio}</TableCell>
              <TableCell>
                {alerta.primeira_acao_em ? formatarDataHora(alerta.primeira_acao_em) : 'Sem ação'}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {alerta.tempo_segundos === null ? '—' : formatarDuracao(alerta.tempo_segundos)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  )
}
