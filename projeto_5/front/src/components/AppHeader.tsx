import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface AppHeaderProps {
  nome: string
  papeis: string[]
  onLogout: () => void
}

// Cabeçalho comum das telas logadas (EQP-15).
export function AppHeader({ nome, papeis, onLogout }: AppHeaderProps) {
  return (
    <header className="flex items-center justify-between border-b bg-card px-6 py-3">
      <span className="font-heading font-semibold">Sala de Situação | Vigidesastres</span>
      <div className="flex items-center gap-4 text-sm">
        <span>
          {nome} <span className="text-muted-foreground">({papeis.join(', ')})</span>
        </span>
        <Button variant="outline" size="sm" onClick={onLogout}>
          <LogOut />
          Sair
        </Button>
      </div>
    </header>
  )
}
