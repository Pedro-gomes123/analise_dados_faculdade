import { useId } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

interface CheckboxGroupProps<T extends string> {
  legend: string
  options: { valor: T; rotulo: string }[]
  value: T[]
  onChange: (value: T[]) => void
}

// Escolha múltipla com rótulo; devolve os valores na ordem das opções.
export function CheckboxGroup<T extends string>({
  legend,
  options,
  value,
  onChange,
}: CheckboxGroupProps<T>) {
  const baseId = useId()

  function toggle(opcao: T, marcado: boolean) {
    const selecionados = new Set(value)
    if (marcado) selecionados.add(opcao)
    else selecionados.delete(opcao)
    onChange(options.map((o) => o.valor).filter((v) => selecionados.has(v)))
  }

  return (
    <fieldset className="grid gap-2">
      <legend className="mb-2 text-sm font-medium">{legend}</legend>
      {options.map((opcao) => {
        const id = `${baseId}-${opcao.valor}`
        return (
          <div key={opcao.valor} className="flex items-center gap-2">
            <Checkbox
              id={id}
              checked={value.includes(opcao.valor)}
              onCheckedChange={(marcado) => toggle(opcao.valor, marcado === true)}
            />
            <Label htmlFor={id} className="font-normal">
              {opcao.rotulo}
            </Label>
          </div>
        )
      })}
    </fieldset>
  )
}
