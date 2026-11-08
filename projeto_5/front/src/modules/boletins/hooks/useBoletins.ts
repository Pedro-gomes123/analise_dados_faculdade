import { useMutation } from '@tanstack/react-query'
import { baixarArquivo } from '@/lib/download'
import { gerarBoletimPdf, preVisualizarBoletim } from '@/modules/boletins/service/boletins.service'

// POST sem efeito no servidor: nada a invalidar.
export function usePreVisualizarBoletim() {
  return useMutation({ mutationFn: preVisualizarBoletim })
}

export function useGerarBoletimPdf() {
  return useMutation({
    mutationFn: gerarBoletimPdf,
    onSuccess: ({ arquivo, nome }) => baixarArquivo(arquivo, nome),
  })
}
