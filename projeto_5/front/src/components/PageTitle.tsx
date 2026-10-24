import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

interface PageTitleProps {
  icon: LucideIcon
  title: string
  description: string
  // Botão principal da página, à direita.
  children?: ReactNode
}

export function PageTitle({ icon: Icon, title, description, children }: PageTitleProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-lg border bg-primary/5 text-primary">
          <Icon className="size-5" />
        </span>
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </div>
  )
}
