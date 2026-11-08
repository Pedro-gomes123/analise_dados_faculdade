import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronRight, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CabecalhoProps {
  trilha?: { secao: string; pagina: string }
  // Botão do menu móvel, à esquerda.
  menu: ReactNode
}

export function Cabecalho({ trilha, menu }: CabecalhoProps) {
  const queryClient = useQueryClient()

  return (
    <header className="flex h-14 items-center gap-2 border-b px-4 md:px-6">
      {menu}
      {trilha && (
        <nav aria-label="Trilha" className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
          <span>{trilha.secao}</span>
          <ChevronRight className="size-4 shrink-0" />
          <span className="truncate text-foreground" aria-current="page">
            {trilha.pagina}
          </span>
        </nav>
      )}
      {/* Busca de novo tudo o que está na tela, sem recarregar a página. */}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Recarregar dados"
        className="ml-auto"
        onClick={() => void queryClient.invalidateQueries()}
      >
        <RefreshCw />
      </Button>
    </header>
  )
}
