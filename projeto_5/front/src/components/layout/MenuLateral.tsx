import { Link } from '@tanstack/react-router'
import { LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { SecaoDoMenu } from '@/components/layout/navegacao'

interface ConteudoDoMenuProps {
  secoes: SecaoDoMenu[]
  nome: string
  papeis: string[]
  onLogout: () => void
  // O menu móvel fecha ao escolher um destino.
  aoNavegar?: () => void
}

// Menu fixo à esquerda a partir de 768 px; abaixo disso abre pelo MenuMovel.
export function MenuLateral(props: ConteudoDoMenuProps) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col gap-6 p-4 md:flex">
      <ConteudoDoMenu {...props} />
    </aside>
  )
}

export function ConteudoDoMenu({ secoes, nome, papeis, onLogout, aoNavegar }: ConteudoDoMenuProps) {
  return (
    <>
      <Link to="/" className="flex items-center gap-2 px-2" onClick={aoNavegar}>
        <span className="flex size-8 items-center justify-center rounded-md bg-primary font-bold text-primary-foreground">
          V
        </span>
        <span className="leading-tight">
          <span className="block font-semibold">O Vigia</span>
          <span className="block text-xs text-muted-foreground">Sala de situação</span>
        </span>
      </Link>

      <nav aria-label="Menu principal" className="flex flex-col gap-5">
        {secoes.map((secao) => (
          <div key={secao.titulo}>
            <p className="mb-1 px-2 text-xs text-muted-foreground">{secao.titulo}</p>
            <ul className="flex flex-col gap-0.5">
              {secao.itens.map(({ rota, codigo, titulo, icone: Icone }) => (
                <li key={rota}>
                  <Link
                    to={rota}
                    onClick={aoNavegar}
                    className="flex items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-sm hover:bg-accent"
                    activeProps={{ className: 'border-border bg-background font-medium shadow-xs' }}
                  >
                    <Icone className="size-4 shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{titulo}</span>
                    {codigo !== 'ADM' && (
                      <span className="text-xs text-muted-foreground">{codigo}</span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-3 rounded-xl border bg-background p-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{nome}</p>
          <p className="truncate text-xs text-muted-foreground">{papeis.join(', ')}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onLogout}>
          <LogOut />
          Sair
        </Button>
      </div>
    </>
  )
}
