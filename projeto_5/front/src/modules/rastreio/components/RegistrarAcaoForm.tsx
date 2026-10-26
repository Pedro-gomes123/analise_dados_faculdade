import { useId, useState, type FormEvent } from 'react'
import { ClipboardPlus } from 'lucide-react'
import { ErrorAlert } from '@/components/ErrorAlert'
import { SelectField } from '@/components/SelectField'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { describeApiError } from '@/lib/http'
import { useAlertasQuery } from '@/modules/alertas/hooks/useAlertas'
import { useCriarAcao } from '@/modules/rastreio/hooks/useRastreio'

const SEM_ALERTA = ''
const DESCRICAO_MAX = 2000

// FLX-003 / RN-004: autor e horário são do servidor; aqui só o que foi feito e,
// se houver, o alerta que motivou a ação (RN-006).
export function RegistrarAcaoForm() {
  const descricaoId = useId()
  const [descricao, setDescricao] = useState('')
  const [idAlerta, setIdAlerta] = useState(SEM_ALERTA)
  const [registrada, setRegistrada] = useState(false)
  const ativos = useAlertasQuery({ page: 1, status: 'ATIVO' })
  const criar = useCriarAcao()

  const opcoes = [
    { valor: SEM_ALERTA, rotulo: 'Sem alerta relacionado' },
    ...(ativos.data?.data ?? []).map((a) => ({
      valor: String(a.id),
      rotulo: `#${a.id} · ${a.nivel} · ${a.parametro.variavel} em ${a.territorio}`,
    })),
  ]

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setRegistrada(false)
    criar.mutate(
      {
        descricao: descricao.trim(),
        ...(idAlerta !== SEM_ALERTA && { id_alerta: Number(idAlerta) }),
      },
      {
        onSuccess: () => {
          setDescricao('')
          setIdAlerta(SEM_ALERTA)
          setRegistrada(true)
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4 rounded-xl border p-4" noValidate>
      <div className="grid gap-2">
        <Label htmlFor={descricaoId}>O que foi feito</Label>
        <Textarea
          id={descricaoId}
          required
          maxLength={DESCRICAO_MAX}
          placeholder="Ex.: equipe de vigilância enviada ao território"
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
        />
      </div>
      <SelectField
        label="Alerta relacionado"
        options={opcoes}
        value={idAlerta}
        onChange={(e) => setIdAlerta(e.target.value)}
      />

      {criar.isError && <ErrorAlert>{describeApiError(criar.error)}</ErrorAlert>}
      {registrada && (
        <p role="status" className="text-sm text-green-700">
          Ação registrada.
        </p>
      )}

      <div className="flex justify-end">
        <Button type="submit" disabled={descricao.trim() === '' || criar.isPending}>
          <ClipboardPlus />
          {criar.isPending ? 'Registrando...' : 'Registrar ação'}
        </Button>
      </div>
    </form>
  )
}
