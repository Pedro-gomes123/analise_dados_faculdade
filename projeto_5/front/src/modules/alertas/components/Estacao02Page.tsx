import { PageTitle } from '@/components/PageTitle'
import { itemDoPapel } from '@/components/layout/navegacao'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertasPanel } from '@/modules/alertas/components/AlertasPanel'
import { ParametrosPanel } from '@/modules/alertas/components/ParametrosPanel'

// REQ-009: EST-02 (Gestor). Mapa e linha do tempo entram nas TASKs 026 e 041.
export function Estacao02Page() {
  const { codigo, titulo, descricao, icone } = itemDoPapel('GES')

  return (
    <>
      <PageTitle icon={icone} title={`${codigo} · ${titulo}`} description={descricao} />
      <Tabs defaultValue="alertas">
        <TabsList>
          <TabsTrigger value="alertas">Alertas</TabsTrigger>
          <TabsTrigger value="parametros">Parâmetros</TabsTrigger>
        </TabsList>
        <TabsContent value="alertas" className="pt-4">
          <AlertasPanel />
        </TabsContent>
        <TabsContent value="parametros" className="pt-4">
          <ParametrosPanel podeEditar />
        </TabsContent>
      </Tabs>
    </>
  )
}
