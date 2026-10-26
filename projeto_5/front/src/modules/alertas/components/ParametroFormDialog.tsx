import { useState, type FormEvent } from 'react'
import { ErrorAlert } from '@/components/ErrorAlert'
import { FormField } from '@/components/FormField'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { formatarNumero, lerNumero } from '@/lib/format'
import { describeApiError } from '@/lib/http'
import { useAlterarParametro, useCriarParametro } from '@/modules/alertas/hooks/useAlertas'
import type { ParametroAlerta } from '@/modules/alertas/types'

interface ParametroFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Sem parâmetro: cadastro. Com parâmetro: edição de limiar e nível. */
  parametro?: ParametroAlerta
}

export function ParametroFormDialog({ open, onOpenChange, parametro }: ParametroFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{parametro ? 'Editar parâmetro' : 'Novo parâmetro'}</DialogTitle>
          <DialogDescription>
            Toda alteração fica no histórico, com autor e valores anterior e novo.
          </DialogDescription>
        </DialogHeader>
        {open && (
          <ParametroForm
            key={parametro?.id ?? 'novo'}
            parametro={parametro}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function ParametroForm({ parametro, onDone }: { parametro?: ParametroAlerta; onDone: () => void }) {
  const [variavel, setVariavel] = useState(parametro?.variavel ?? '')
  const [territorio, setTerritorio] = useState(parametro?.territorio ?? '')
  const [limiar, setLimiar] = useState(parametro ? formatarNumero(parametro.limiar) : '')
  const [nivel, setNivel] = useState(parametro?.nivel ?? '')
  const criar = useCriarParametro()
  const alterar = useAlterarParametro()
  const mutation = parametro ? alterar : criar

  const limiarLido = lerNumero(limiar)
  const limiarInvalido = limiar.trim() !== '' && limiarLido === null
  const podeSalvar =
    variavel.trim() !== '' &&
    territorio.trim() !== '' &&
    nivel.trim() !== '' &&
    limiarLido !== null &&
    !mutation.isPending

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (limiarLido === null) return
    if (parametro) {
      alterar.mutate(
        { id: parametro.id, dados: { limiar: limiarLido, nivel: nivel.trim() } },
        { onSuccess: onDone },
      )
      return
    }
    criar.mutate(
      {
        variavel: variavel.trim(),
        territorio: territorio.trim(),
        limiar: limiarLido,
        nivel: nivel.trim(),
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
      {/* Variável e território identificam o parâmetro: não mudam na edição. */}
      <FormField
        label="Variável"
        required
        disabled={!!parametro}
        value={variavel}
        onChange={(e) => setVariavel(e.target.value)}
      />
      <FormField
        label="Território"
        required
        disabled={!!parametro}
        value={territorio}
        onChange={(e) => setTerritorio(e.target.value)}
      />
      <FormField
        label="Limiar"
        inputMode="decimal"
        required
        aria-invalid={limiarInvalido}
        value={limiar}
        onChange={(e) => setLimiar(e.target.value)}
      />
      {limiarInvalido && <p className="-mt-2 text-sm text-destructive">Informe um número</p>}
      {/* Escala de níveis não documentada (DUV-010): texto livre por enquanto. */}
      <FormField label="Nível" required value={nivel} onChange={(e) => setNivel(e.target.value)} />

      {mutation.isError && <ErrorAlert>{describeApiError(mutation.error)}</ErrorAlert>}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancelar
        </Button>
        <Button type="submit" disabled={!podeSalvar}>
          {mutation.isPending ? 'Salvando...' : 'Salvar'}
        </Button>
      </DialogFooter>
    </form>
  )
}
