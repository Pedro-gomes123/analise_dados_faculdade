import { ErrorAlert } from '@/components/ErrorAlert'
import { Button } from '@/components/ui/button'
import { useHealthQuery } from '@/modules/health/hooks/useHealthQuery'

export function ApiStatus() {
  const { data, isPending, isError, refetch } = useHealthQuery()

  if (isPending) {
    return <p className="text-muted-foreground">Verificando a API...</p>
  }

  if (isError || data.status !== 'ok') {
    return (
      <ErrorAlert
        action={
          <Button variant="outline" size="sm" onClick={() => void refetch()}>
            Tentar de novo
          </Button>
        }
      >
        API indisponível.
      </ErrorAlert>
    )
  }

  return <p className="text-green-700">API e banco de dados funcionando.</p>
}
