import { ClipboardCheck, Siren } from 'lucide-react'
import { formatarDataHora, formatarNumero } from '@/lib/format'
import type { ItemLinhaDoTempo } from '@/modules/rastreio/types'

// RN-005: alertas e ações em ordem cronológica (a ordem vem do back).
export function LinhaDoTempoLista({ itens }: { itens: ItemLinhaDoTempo[] }) {
  if (itens.length === 0) {
    return <p className="text-sm text-muted-foreground">Nada registrado no período.</p>
  }

  return (
    <ol aria-label="Linha do tempo" className="relative grid gap-4 border-l pl-6">
      {itens.map((item) => {
        const alerta = item.tipo === 'ALERTA'
        const Icone = alerta ? Siren : ClipboardCheck
        return (
          <li key={`${item.tipo}-${alerta ? item.alerta.id : item.acao.id}`} className="relative">
            <span
              className={`absolute -left-9 flex size-6 items-center justify-center rounded-full border bg-background ${
                alerta ? 'text-destructive' : 'text-primary'
              }`}
            >
              <Icone className="size-3.5" />
            </span>
            <p className="text-xs text-muted-foreground">{formatarDataHora(item.em)}</p>
            {alerta ? (
              <p className="text-sm">
                <span className="font-medium">
                  Alerta {item.alerta.nivel} · {item.alerta.variavel} em {item.alerta.territorio}
                </span>
                <span className="text-muted-foreground">
                  {' '}
                  — leitura {formatarNumero(item.alerta.valor_lido)} (limiar{' '}
                  {formatarNumero(item.alerta.limiar)})
                </span>
              </p>
            ) : (
              <p className="text-sm">
                <span className="font-medium">{item.acao.descricao}</span>
                <span className="text-muted-foreground">
                  {' '}
                  — {item.acao.autor.nome}
                  {item.acao.id_alerta !== null && ` · alerta #${item.acao.id_alerta}`}
                </span>
              </p>
            )}
          </li>
        )
      })}
    </ol>
  )
}
