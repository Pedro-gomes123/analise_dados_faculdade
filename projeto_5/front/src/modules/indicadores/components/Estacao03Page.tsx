import { PageTitle } from '@/components/PageTitle'
import { itemDoPapel } from '@/components/layout/navegacao'
import { TempoAcionamentoPanel } from '@/modules/indicadores/components/TempoAcionamentoPanel'

// REQ-010: EST-03 (Gestão Institucional). Pessoas em risco e cobertura de
// resposta dependem do gold (DEC-009, TASK-042).
export function Estacao03Page() {
  const { codigo, titulo, descricao, icone } = itemDoPapel('GIN')

  return (
    <>
      <PageTitle icon={icone} title={`${codigo} · ${titulo}`} description={descricao} />
      <TempoAcionamentoPanel />
    </>
  )
}
