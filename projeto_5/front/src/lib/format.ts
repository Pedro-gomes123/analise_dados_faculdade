// Datas chegam em UTC (DEC-017) e são mostradas no horário do Recife.
const formatoDataHora = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Recife',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const formatoNumero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })

// "2026-10-24T13:05:00Z" → "24/10/2026 10:05"
export function formatarDataHora(iso: string): string {
  return formatoDataHora.format(new Date(iso)).replace(', ', ' ')
}

// 1234.5 → "1.234,5"; até 3 casas, como o decimal(12,3) do banco
export function formatarNumero(valor: number): string {
  return formatoNumero.format(valor)
}

// Número digitado em pt-BR ("62,5" ou "1.234,5") → 62.5 / 1234.5; null se não for número.
export function lerNumero(texto: string): number | null {
  const limpo = texto.trim().replace(/\./g, '').replace(',', '.')
  if (limpo === '' || !/^-?\d+(\.\d+)?$/.test(limpo)) return null
  return Number(limpo)
}

// Duração em segundos para leitura rápida: 45 → "45 s"; 2280 → "38 min"; 3900 → "1 h 05 min".
export function formatarDuracao(segundos: number): string {
  if (segundos < 60) return `${segundos} s`
  const minutos = Math.round(segundos / 60)
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  return `${horas} h ${String(minutos % 60).padStart(2, '0')} min`
}
