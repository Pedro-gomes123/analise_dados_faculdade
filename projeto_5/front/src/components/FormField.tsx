import { useId, type ComponentProps } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface FormFieldProps extends ComponentProps<typeof Input> {
  label: string
}

// Rótulo + campo ligados por id; base de todos os formulários.
export function FormField({ label, id, ...props }: FormFieldProps) {
  const generatedId = useId()
  const fieldId = id ?? generatedId

  return (
    <div className="grid gap-2">
      <Label htmlFor={fieldId}>{label}</Label>
      <Input id={fieldId} {...props} />
    </div>
  )
}
