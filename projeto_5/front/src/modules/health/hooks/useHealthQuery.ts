import { useQuery } from '@tanstack/react-query'
import { getHealth } from '@/modules/health/service/health.service'

export const healthKeys = {
  all: ['health'] as const,
}

export function useHealthQuery() {
  return useQuery({
    queryKey: healthKeys.all,
    queryFn: getHealth,
    refetchInterval: 30_000,
  })
}
