import { PageTitle } from '@/components/PageTitle'
import { itemDoPapel } from '@/components/layout/navegacao'
import { ComposicaoBoletim } from '@/modules/boletins/components/ComposicaoBoletim'

// REQ-011: EST-04 (Comunicação). Meteorologia e rios dependem do gold
// (DEC-009, TASK-032); riscos e contatos, da DUV-033 (PR-022 c).
export function Estacao04Page() {
  const { codigo, titulo, descricao, icone } = itemDoPapel('COM')

  return (
    <>
      <PageTitle icon={icone} title={`${codigo} · ${titulo}`} description={descricao} />
      <ComposicaoBoletim />
    </>
  )
}
