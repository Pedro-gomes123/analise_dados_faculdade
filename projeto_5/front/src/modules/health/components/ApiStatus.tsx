import { useHealthQuery } from '@/modules/health/hooks/useHealthQuery'

export function ApiStatus() {
  const { data, isPending, isError, refetch } = useHealthQuery()

  if (isPending) {
    return <p className="text-slate-500">Verificando a API...</p>
  }

  if (isError || data.status !== 'ok') {
    return (
      <div role="alert" className="flex items-center gap-3 text-red-700">
        <span>API indisponível.</span>
        <button
          type="button"
          className="rounded border border-red-300 px-2 py-1 text-sm hover:bg-red-50"
          onClick={() => void refetch()}
        >
          Tentar de novo
        </button>
      </div>
    )
  }

  return <p className="text-green-700">API e banco de dados funcionando.</p>
}
