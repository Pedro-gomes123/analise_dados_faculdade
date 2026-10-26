import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PERIODOS, type Periodo } from '@/lib/periodo'

interface PeriodoTabsProps {
  value: Periodo
  onChange: (periodo: Periodo) => void
}

// Seletor de período comum às consultas por período (PR-018).
export function PeriodoTabs({ value, onChange }: PeriodoTabsProps) {
  return (
    <Tabs value={value} onValueChange={(valor) => onChange(valor as Periodo)}>
      <TabsList aria-label="Período">
        {PERIODOS.map((p) => (
          <TabsTrigger key={p.valor} value={p.valor}>
            {p.rotulo}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
