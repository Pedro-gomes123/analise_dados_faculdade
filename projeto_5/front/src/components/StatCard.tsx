import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string
  hint?: string
}

// Cartão de indicador: rótulo, valor em destaque e uma linha de contexto.
export function StatCard({ icon: Icon, label, value, hint }: StatCardProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="flex size-7 items-center justify-center rounded-md bg-muted">
          <Icon className="size-3.5" />
        </span>
        {label}
      </div>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}
