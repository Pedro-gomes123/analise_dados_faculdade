import type { ReactNode } from 'react'

interface PageTitleProps {
  title: string
  children?: ReactNode
}

export function PageTitle({ title, children }: PageTitleProps) {
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <h1 className="font-heading text-2xl font-semibold">{title}</h1>
      {children}
    </div>
  )
}
