import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface PaginacaoProps {
  page: number
  totalPages: number
  totalItems: number
  onPageChange: (page: number) => void
}

export function Paginacao({ page, totalPages, totalItems, onPageChange }: PaginacaoProps) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm text-muted-foreground">
      <span>
        {totalItems} {totalItems === 1 ? 'registro' : 'registros'}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft />
          Anterior
        </Button>
        <span>
          Página {page} de {Math.max(totalPages, 1)}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          Próxima
          <ChevronRight />
        </Button>
      </div>
    </div>
  )
}
