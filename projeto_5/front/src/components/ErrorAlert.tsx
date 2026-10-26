import type { ReactNode } from 'react'
import { CircleAlert } from 'lucide-react'
import { Alert, AlertAction, AlertDescription } from '@/components/ui/alert'

interface ErrorAlertProps {
  children: ReactNode
  action?: ReactNode
}

export function ErrorAlert({ children, action }: ErrorAlertProps) {
  return (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertDescription>{children}</AlertDescription>
      {action && <AlertAction>{action}</AlertAction>}
    </Alert>
  )
}
