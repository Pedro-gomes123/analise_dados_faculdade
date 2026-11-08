import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatarDataHora, formatarNumero } from '@/lib/format'
import type { Alerta } from '@/modules/alertas/types'

// REQ-005 (2): fonte e hora da leitura. O destaque por cor de nível depende da
// escala (DUV-010); até lá o nível aparece como texto.
export function AlertasTable({ alertas }: { alertas: Alerta[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Nível</TableHead>
          <TableHead>Variável</TableHead>
          <TableHead>Território</TableHead>
          <TableHead className="text-right">Leitura / limiar</TableHead>
          <TableHead>Fonte</TableHead>
          <TableHead>Lida em</TableHead>
          <TableHead>Disparado em</TableHead>
          <TableHead>Situação</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alertas.length === 0 && (
          <TableRow>
            <TableCell colSpan={8} className="text-center text-muted-foreground">
              Nenhum alerta encontrado.
            </TableCell>
          </TableRow>
        )}
        {alertas.map((alerta) => (
          <TableRow key={alerta.id}>
            <TableCell>
              <Badge variant="secondary">{alerta.nivel}</Badge>
            </TableCell>
            <TableCell>{alerta.parametro.variavel}</TableCell>
            <TableCell>{alerta.territorio}</TableCell>
            <TableCell className="text-right tabular-nums">
              <span className="font-medium">{formatarNumero(alerta.valor_lido)}</span>
              <span className="text-muted-foreground"> / {formatarNumero(alerta.parametro.limiar)}</span>
            </TableCell>
            <TableCell>{alerta.fonte}</TableCell>
            <TableCell>{formatarDataHora(alerta.lida_em)}</TableCell>
            <TableCell>{formatarDataHora(alerta.disparado_em)}</TableCell>
            <TableCell>
              <Badge variant={alerta.status === 'ATIVO' ? 'destructive' : 'outline'}>
                {alerta.status === 'ATIVO' ? 'Ativo' : 'Encerrado'}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
