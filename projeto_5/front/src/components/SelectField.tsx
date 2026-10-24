import { useId, type ComponentProps } from 'react'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface SelectFieldProps extends ComponentProps<'select'> {
  label: string
  options: { valor: string; rotulo: string }[]
}

// Lista de escolha nativa com rótulo, no mesmo visual do Input.
export function SelectField({ label, options, id, className, ...props }: SelectFieldProps) {
  const generatedId = useId()
  const fieldId = id ?? generatedId

  return (
    <div className="grid gap-2">
      <Label htmlFor={fieldId}>{label}</Label>
      <select
        id={fieldId}
        className={cn(
          'h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none',
          'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50',
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
    </div>
  )
}
