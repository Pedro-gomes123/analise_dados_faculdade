import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import { ErrorAlert } from '@/components/ErrorAlert'
import { Button } from '@/components/ui/button'
import { describeApiError } from '@/lib/http'

interface QueryResultProps<T> {
  query: UseQueryResult<T>
  children: (data: T) => ReactNode
}

// Carregando, erro com "Tentar de novo" ou o conteúdo: o mesmo em toda tela.
export function QueryResult<T>({ query, children }: QueryResultProps<T>) {
  if (query.isPending) return <p className="text-sm text-muted-foreground">Carregando...</p>
  if (query.isError) {
    return (
      <ErrorAlert
        action={
          <Button variant="outline" size="sm" onClick={() => void query.refetch()}>
            Tentar de novo
          </Button>
        }
      >
        {describeApiError(query.error)}
      </ErrorAlert>
    )
  }
  return <>{children(query.data)}</>
}
