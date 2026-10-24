import { createFileRoute } from '@tanstack/react-router'
import { ApiStatus } from '@/modules/health/components/ApiStatus'

export const Route = createFileRoute('/')({
  component: HomePage,
})

// Página técnica provisória: as telas do produto dependem dos requisitos aprovados e do mockup.
function HomePage() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">Sala de Situação | Vigidesastres</h1>
      <div className="mt-4">
        <ApiStatus />
      </div>
    </main>
  )
}
