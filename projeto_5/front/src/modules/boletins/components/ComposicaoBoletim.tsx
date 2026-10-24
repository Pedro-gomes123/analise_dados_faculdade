import { useState } from 'react'
import { Eye, FileDown } from 'lucide-react'
import { CheckboxGroup } from '@/components/CheckboxGroup'
import { ErrorAlert } from '@/components/ErrorAlert'
import { Button } from '@/components/ui/button'
import { describeApiError } from '@/lib/http'
import { useGerarBoletimPdf, usePreVisualizarBoletim } from '@/modules/boletins/hooks/useBoletins'
import { SECOES_BOLETIM, type SecaoBoletim } from '@/modules/boletins/types'

const TODAS = SECOES_BOLETIM.map((s) => s.valor)

// FLX-004: escolhe as seções, pré-visualiza e só então gera o PDF, com as
// mesmas seções da pré-visualização (RN-009 #4). Publicação manual (AM-005).
export function ComposicaoBoletim() {
  const [secoes, setSecoes] = useState<SecaoBoletim[]>(TODAS)
  const previa = usePreVisualizarBoletim()
  const pdf = useGerarBoletimPdf()

  function trocarSecoes(novas: SecaoBoletim[]) {
    setSecoes(novas)
    // A pré-visualização mostrada deixa de valer para a nova escolha.
    previa.reset()
    pdf.reset()
  }

  const semSecao = secoes.length === 0
  const erro = previa.error ?? pdf.error

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <div className="grid content-start gap-4 rounded-xl border p-4">
        <CheckboxGroup
          legend="Seções do boletim"
          options={SECOES_BOLETIM}
          value={secoes}
          onChange={trocarSecoes}
        />
        {semSecao && (
          <p className="text-sm text-muted-foreground">Escolha ao menos uma seção.</p>
        )}
        {erro && <ErrorAlert>{describeApiError(erro)}</ErrorAlert>}
        <div className="grid gap-2">
          <Button
            variant="outline"
            disabled={semSecao || previa.isPending}
            onClick={() => previa.mutate(secoes)}
          >
            <Eye />
            {previa.isPending ? 'Gerando pré-visualização...' : 'Pré-visualizar'}
          </Button>
          <Button
            disabled={previa.data === undefined || pdf.isPending}
            onClick={() => pdf.mutate(secoes)}
          >
            <FileDown />
            {pdf.isPending ? 'Gerando PDF...' : 'Gerar boletim pronto para publicação'}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          O PDF é baixado para publicação manual nos canais de divulgação.
        </p>
      </div>

      {previa.data === undefined ? (
        <div className="flex min-h-96 items-center justify-center rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          Escolha as seções e clique em Pré-visualizar.
        </div>
      ) : (
        // sandbox vazio: o HTML do boletim não executa script nem navega.
        <iframe
          title="Pré-visualização do boletim"
          srcDoc={previa.data}
          sandbox=""
          className="h-[70vh] min-h-96 w-full rounded-xl border bg-white"
        />
      )}
    </div>
  )
}
