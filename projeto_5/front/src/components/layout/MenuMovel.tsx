import { useState, type ComponentProps } from 'react'
import { Menu } from 'lucide-react'
import { ConteudoDoMenu } from '@/components/layout/MenuLateral'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'

type MenuMovelProps = Omit<ComponentProps<typeof ConteudoDoMenu>, 'aoNavegar'>

// Abaixo de 768 px o menu lateral não cabe ao lado da página e abre por cima dela.
export function MenuMovel(props: MenuMovelProps) {
  const [aberto, setAberto] = useState(false)

  return (
    <Sheet open={aberto} onOpenChange={setAberto}>
      <SheetTrigger asChild>
        <Button type="button" variant="ghost" size="icon" aria-label="Abrir menu" className="md:hidden">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 gap-6 overflow-y-auto p-4" aria-describedby={undefined}>
        <SheetTitle className="sr-only">Menu</SheetTitle>
        <ConteudoDoMenu {...props} aoNavegar={() => setAberto(false)} />
      </SheetContent>
    </Sheet>
  )
}
