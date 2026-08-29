# Arquitetura Medalhão no Azure SQL Database

Guia conceitual para implementar a arquitetura medalhão (bronze, silver, gold) usando um único Azure SQL Database com schemas como camadas.

---

## 1. A decisão de desenho

A ideia original era usar um database para cada camada. No Azure SQL Database isso não funciona bem, porque os bancos são isolados entre si: uma procedure em um banco não consegue gravar diretamente em outro. Consultas entre bancos exigem Elastic Query (tabelas externas), que é trabalhoso, limitado e lento. Além disso, a oferta gratuita cobre apenas um banco — três databases significariam custo extra.

**Solução adotada:** um único database com três schemas, um para cada camada.

| Abordagem | Viável no Azure SQL DB? | Observação |
|---|---|---|
| 3 databases separados | Não recomendado | Bancos isolados; procedures não cruzam bancos; custo triplicado |
| 1 database com 3 schemas | Recomendado | Procedures acessam todas as camadas; permissões por schema; custo único |

O schema funciona como o "sobrenome" da tabela e indica o estágio de qualidade do dado: `bronze.vendas`, `silver.vendas`, `gold.faturamento_mensal`. O schema `dbo` (padrão) fica de lado ou é usado apenas para objetos administrativos — ele não é uma camada.

---

## 2. As três camadas

### Bronze — dado cru

- Fotografia fiel da fonte: grava como veio, com erros, duplicatas e tudo.
- Nenhuma correção, filtro ou transformação.
- Serve como histórico bruto e rede de segurança: se um tratamento estiver errado, reprocessa-se a partir do bronze sem voltar à origem.
- Único ponto de escrita: o pipeline de ingestão.

### Silver — dado limpo

- A "verdade limpa" do negócio, ainda em nível de detalhe (linha a linha).
- Tratamentos típicos: correção de tipos, remoção de duplicatas, tratamento de nulos, padronização (datas, textos), junções entre fontes diferentes.
- Alimentado exclusivamente por procedures que leem do bronze.

### Gold — dado pronto para consumo

- Modelado para responder às perguntas do negócio: agregações, rankings, modelagem dimensional (estrela).
- Quem consome o gold não faz transformação nenhuma — só lê.
- Alimentado por procedures que leem do silver.
- Única camada exposta a dashboards, relatórios e BI.

---

## 3. O fluxo completo

```
Fontes de dados (CSV, APIs, sistemas)
        │
        ▼  pipeline de ingestão (Data Factory ou script)
┌─────────────────────────────────────┐
│         Azure SQL Database          │
│                                     │
│   schema bronze  (dados crus)       │
│        │                            │
│        ▼  procedure de limpeza      │
│   schema silver  (dados limpos)     │
│        │                            │
│        ▼  procedure de agregação    │
│   schema gold    (dados p/ consumo) │
└─────────────────────────────────────┘
        │
        ▼
Consumo (Power BI, relatórios, dashboards)
```

Responsabilidades de cada peça:

1. **Pipeline externo** — único que escreve no bronze; despeja os dados exatamente como vieram.
2. **Procedure de limpeza** — lê do bronze, trata e grava no silver; pertence conceitualmente à camada silver.
3. **Procedure de agregação** — lê do silver, modela/agrega e grava no gold.
4. **Consumidores** — leem somente do gold, nunca do bronze ou silver.

---

## 4. Regras conceituais

**Fluxo em sentido único.** Dados só andam para frente (bronze → silver → gold). Nenhuma procedure escreve de volta em camada anterior e nada pula camada (o pipeline nunca grava direto no silver). Quebrar essa regra destrói a rastreabilidade — saber de onde cada número veio.

**Separação entre transformação e orquestração.** As procedures transformam; algo externo (o orquestrador, ex.: Azure Data Factory) dispara tudo na ordem certa e lida com falhas. São responsabilidades distintas: ingestão bronze → executa procedures do silver → executa procedures do gold, num pipeline com dependências.

**Idempotência.** Toda carga deve poder rodar duas vezes sem duplicar dados. Cada procedure deixa a camada de destino no estado correto independente de quantas execuções aconteçam — seja recriando os dados, seja atualizando de forma incremental.

**Permissões por schema.** Schemas permitem controle de acesso real: o usuário do Power BI recebe leitura apenas no gold, garantindo que ninguém consuma dado cru por engano. A separação deixa de ser convenção de nome e vira barreira efetiva.

---

## 5. Convenções sugeridas

| Item | Convenção | Exemplo |
|---|---|---|
| Tabela bronze | mesmo nome da fonte | `bronze.vendas` |
| Tabela silver | mesmo nome, limpa | `silver.vendas` |
| Tabela gold | nome da pergunta de negócio | `gold.faturamento_mensal` |
| Procedure de carga | prefixo `carga_` no schema de destino | `silver.carga_vendas` |

---

## 6. Contexto do ambiente (oferta gratuita)

- Azure SQL Database serverless na oferta gratuita: 100.000 segundos de vCore por mês e 32 GB de armazenamento.
- Cobrança excedente desabilitada: ao esgotar o limite mensal, o banco pausa até o mês seguinte — custo zero garantido.
- Pausa automática fixa em 1 hora de inatividade (efetivada em até 1 h10); a primeira conexão após a pausa leva cerca de 1 minuto para o banco retomar.
- Fechar conexões (Editor de Consultas, SSMS, aplicações) ao terminar de usar, para o banco pausar e economizar os segundos gratuitos.

---

## 7. Próximos passos possíveis

- Criar os schemas e as tabelas de cada camada no banco atual.
- Definir a estratégia de carga (completa vs. incremental) de cada procedure.
- Montar o pipeline de orquestração no Azure Data Factory apontando para o banco.
- Configurar permissões de leitura no gold para a ferramenta de BI.