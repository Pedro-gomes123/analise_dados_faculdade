# Arquitetura Medalhão — MongoDB Atlas + Azure SQL Database

Guia conceitual para implementar a arquitetura medalhão (raw, bronze, silver, gold) usando o MongoDB Atlas como camada raw e um único Azure SQL Database com schemas como camadas bronze, silver e gold.

## 1. A decisão de desenho

A ideia original era usar um database para cada camada. No Azure SQL Database isso não funciona bem, porque os bancos são isolados entre si: uma procedure em um banco não consegue gravar diretamente em outro. Consultas entre bancos exigem Elastic Query (tabelas externas), que é trabalhoso, limitado e lento. Além disso, a oferta gratuita cobre apenas um banco — três databases significariam custo extra.

Uma segunda decisão foi **separar a camada raw do banco relacional**. O dado da fonte (API da APAC) chega em JSON, com campos bagunçados, valores sentinela (`-1`), datas em formato inconsistente e até coordenadas erradas. Forçar esse JSON num schema relacional já na entrada seria uma transformação disfarçada — e a camada raw, por definição, não transforma nada. Um banco de documentos aceita o JSON exatamente como veio.

**Solução adotada:** MongoDB Atlas como camada raw (documentos JSON) + um único Azure SQL Database com três schemas (bronze, silver, gold).

| Abordagem | Viável? | Observação |
|---|---|---|
| 3+ databases SQL separados | Não recomendado | Bancos isolados; procedures não cruzam bancos; custo multiplicado |
| Raw dentro do SQL (tabela de JSON) | Possível, não adotado | Consome os 32 GB do banco com dado bruto; JSON em NVARCHAR é desconfortável de consultar |
| **Mongo (raw) + 1 database SQL com 3 schemas** | **Recomendado** | Raw guarda JSON nativo; procedures SQL acessam todas as camadas; custo zero nas duas pontas |

O schema funciona como o "sobrenome" da tabela e indica o estágio de qualidade do dado: `bronze.chuvas_apac`, `silver.chuvas_apac`, `gold.acumulado_semanal_bacia`. O schema `dbo` (padrão) fica de lado ou é usado apenas para objetos administrativos — ele não é uma camada.

## 2. As quatro camadas

### Raw — dado como veio da fonte (MongoDB Atlas)

- Fotografia fiel da origem: o JSON da API entra **sem nenhuma alteração** — com `-1`, datas-string duplicadas, coordenadas erradas e tudo.
- Cada ingestão gera um **snapshot novo** (append), nunca sobrescreve. A API só expõe o estado atual das estações; é o acúmulo de snapshots que constrói o histórico.
- Cada documento carrega um `ingestao_ts` (timestamp de quando a pipeline rodou), que servirá de marca-d'água para a carga incremental.
- Serve como histórico bruto e rede de segurança: se um tratamento posterior estiver errado, reprocessa-se a partir do raw sem voltar à origem.
- Único ponto de escrita: a pipeline de ingestão (Pipeline 1).

Estrutura de cada documento na collection:

```json
{
  "ingestao_ts": "2026-09-06T10:40:00Z",
  "payload": { "...documento da API exatamente como veio..." }
}
```

### Bronze — dado cru estruturado (schema `bronze` no SQL)

- Primeira materialização relacional: o JSON vira linhas e colunas, mas **sem limpeza** — o `-1` continua `-1`, a data continua string.
- A única coluna adicionada é o `ingestao_ts` herdado do raw, que identifica o snapshot.
- Alimentado exclusivamente pela pipeline semanal de carga incremental (Pipeline 2), que lê do Mongo apenas o que ainda não foi carregado.
- Único ponto de escrita: a Pipeline 2.

### Silver — dado limpo

- A "verdade limpa" do negócio, ainda em nível de detalhe (linha a linha).
- Tratamentos típicos deste projeto: converter `-1` em `NULL` (sensor sem dado ≠ chuva negativa), converter a data-string para `DATETIME2`, remover estações com coordenadas fora do bounding box de Pernambuco, remover duplicatas de snapshot, padronizar textos (ex.: fabricante com espaço à esquerda).
- Alimentado exclusivamente por procedures que leem do bronze.

### Gold — dado pronto para consumo

- Modelado para responder às perguntas do negócio: acumulados por bacia, ranking de municípios por chuva, séries temporais agregadas, modelagem dimensional (estrela).
- Quem consome o gold não faz transformação nenhuma — só lê.
- Alimentado por procedures que leem do silver.
- Única camada exposta a dashboards, relatórios e BI.

## 3. O fluxo completo

```
Fonte: API APAC (ArcGIS REST — pluviômetros de PE)
        │
        ▼  Pipeline 1 — ingestão (frequente: horária ou a cada 10 min)
┌─────────────────────────────────────┐
│          MongoDB Atlas (M0)         │
│   collection raw (snapshots JSON)   │
└─────────────────────────────────────┘
        │
        ▼  Pipeline 2 — carga incremental (semanal, por marca-d'água)
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

- **Pipeline 1 (ingestão)** — única que escreve no raw; despeja o JSON da API exatamente como veio, acrescentando apenas o `ingestao_ts`.
- **Pipeline 2 (carga incremental)** — única que escreve no bronze; lê do Mongo os documentos com `ingestao_ts` maior que a marca-d'água e insere no SQL, atualizando a marca ao final.
- **Procedure de limpeza** — lê do bronze, trata e grava no silver; pertence conceitualmente à camada silver.
- **Procedure de agregação** — lê do silver, modela/agrega e grava no gold.
- **Consumidores** — leem somente do gold, nunca das camadas anteriores.

## 4. Ferramentas

| Camada / função | Ferramenta | Custo | Papel |
|---|---|---|---|
| Fonte | API ArcGIS REST da APAC (geoportal.apac.pe.gov.br) | Público | Dados de ~280 pluviômetros de PE (acumulados 1h–72h) |
| Raw | MongoDB Atlas, cluster M0 | Gratuito (512 MB) | Armazena snapshots JSON como vieram |
| Bronze / Silver / Gold | Azure SQL Database serverless (oferta gratuita) | Gratuito (100 mil vCore-s/mês, 32 GB) | Camadas relacionais em schemas |
| Orquestração | Azure Data Factory *(alternativa: Apache Airflow — ver ressalva em 4.3)* | Pago por execução (~US$ 1 / 1.000 activity runs; consome crédito Students) | Dispara as pipelines e as procedures na ordem certa |
| Transformação | Stored procedures T-SQL | Incluído no banco | bronze → silver → gold |
| Consumo | Power BI | Gratuito (Desktop) | Dashboards lendo apenas do gold |
| Organização/custo | Resource Group `teste_v1` + tag `proj:pedro` | Gratuito | Agrupa recursos e permite rastrear custo no Cost Management |

### 4.1 MongoDB Atlas (camada raw)

- Cluster **M0** (free tier): 512 MB de armazenamento, suficiente para meses de snapshots se a ingestão for horária (~7 MB/dia com ~280 estações).
- Se a ingestão for a cada 10 minutos (~40 MB/dia), o M0 esgota em ~2 semanas — nesse caso, expurgar do Mongo os documentos já carregados no bronze (o bronze passa a ser o histórico permanente).
- TLS do Atlas é válido — a conexão não precisa de `verify=False` (diferente da API da APAC, cujo certificado falha na validação).
- O Azure Data Factory possui **conector nativo MongoDB Atlas** (como source), o que viabiliza a Pipeline 2 sem código.

### 4.2 Azure SQL Database (bronze, silver, gold)

- Serverless na **oferta gratuita**: 100.000 segundos de vCore por mês e 32 GB de armazenamento.
- **Cobrança excedente desabilitada**: ao esgotar o limite mensal, o banco pausa até o mês seguinte — custo zero garantido.
- **Pausa automática** após 1 hora de inatividade; a primeira conexão após a pausa leva cerca de 1 minuto para o banco retomar. A carga semanal joga a favor: o banco dorme a semana inteira e só acorda para receber a carga e rodar as procedures.
- Fechar conexões (Editor de Consultas, SSMS, aplicações) ao terminar de usar, para o banco pausar e economizar os segundos gratuitos.
- Habilitar em Rede: "Permitir que serviços do Azure acessem este servidor", para o Data Factory conseguir gravar.

### 4.3 Azure Data Factory (orquestração) — com ressalva para Apache Airflow

- **Pipeline 1 — ingestão no raw:** trigger de agendamento (Schedule) na frequência escolhida; atividade que chama a API REST da APAC e grava no Atlas. No linked service REST, habilitar "Disable certificate validation" (equivalente ao `verify=False`), pois o certificado do geoportal falha na validação.
- **Pipeline 2 — carga incremental no bronze (semanal):** padrão clássico de três passos:
  1. **Lookup** — lê a marca-d'água (`ultimo_ts`) da tabela de controle no SQL;
  2. **Copy Activity** — source Mongo Atlas com filtro `{"ingestao_ts": {"$gt": <ultimo_ts>}}`, sink `bronze.chuvas_apac` (append), com o mapeamento JSON → colunas;
  3. **Script/Stored Procedure** — atualiza a marca-d'água com o maior `ingestao_ts` carregado.
- Após a carga, a mesma pipeline (ou uma pipeline-mãe) executa as procedures do silver e depois as do gold, com dependências de sucesso entre as etapas.
- Configurar **retry** (ex.: 2 tentativas, intervalo de 60 s) nas atividades que tocam o SQL: a primeira conexão pode dar timeout enquanto o banco serverless acorda.
- É o único componente do projeto com custo real por execução — a tag `proj:pedro` permite acompanhar esse gasto no Cost Management.

**Custo estimado do ADF por cenário de ingestão:**

| Frequência da Pipeline 1 | Execuções/mês (aprox.) | Custo estimado/mês* |
|---|---|---|
| A cada 10 min | ~4.320 | poucos US$ (execuções + DIU do Copy) |
| Horária | ~720 | ~US$ 1–2 |
| Horária + carga semanal (Pipeline 2) | ~725 | ~US$ 1–2 |

\* Ordem de grandeza; o Copy Activity cobra também tempo de Data Integration Unit. Acompanhar o valor real no Cost Management filtrando pela tag do projeto.

**Ressalva — Apache Airflow como alternativa:** se o custo do ADF se mostrar relevante para o orçamento (ou quando o crédito do Azure for Students expirar), a orquestração pode migrar para o **Apache Airflow**, que é open source e gratuito como software. Pontos a considerar:

- **Autogerenciado (custo ≈ zero):** rodar o Airflow em Docker na máquina local ou numa VM pequena elimina o custo por execução. Em troca, perde-se o gerenciado: a máquina precisa estar ligada nos horários dos agendamentos, e instalação, upgrades e monitoramento ficam por conta do time. Para pipelines horárias, uma alternativa local ainda mais simples é `cron` + os scripts Python já prototipados.
- **Gerenciado no Azure (custo maior, não menor):** o próprio Data Factory oferece **Workflow Orchestration Manager** (Airflow gerenciado), mas ele cobra por hora de ambiente ligado — sai mais caro que as execuções avulsas do ADF neste volume. Só faz sentido se o projeto crescer para muitas DAGs complexas.
- **Tradução dos conceitos:** as pipelines viram DAGs Python; o padrão de marca-d'água permanece idêntico (ler `ultimo_ts` → extrair do Mongo → carregar no bronze → atualizar marca); os operadores `HttpOperator`/`PythonOperator` (ingestão), `MongoHook` e `MsSqlOperator`/`ODBC` cobrem as conexões. O retry para o banco serverless acordando é configuração nativa de task (`retries`, `retry_delay`).
- **Critério de decisão:** enquanto o custo mensal do ADF ficar na casa de poucos dólares e houver crédito Students, o ADF compensa pela simplicidade (conectores prontos, sem infraestrutura). Revisar a decisão se o custo passar de ~US$ 5–10/mês ou ao fim do crédito.

### 4.4 Ingestão — detalhe da chamada à API

A pipeline de ingestão consulta o endpoint `.../MapServer/6/query` com filtro pelos últimos minutos, no mesmo espírito do protótipo em Python:

```
where = ultima_leitura_data_hora >= '<agora - janela>'
outFields = *
f = json
```

Atenção ao fuso: no Data Factory, `utcNow()` retorna UTC; o campo da APAC está em hora local de Recife (UTC-3). A expressão da janela precisa compensar (ex.: `addMinutes(utcNow(), -190)` para janela de 10 minutos).

## 5. Regras conceituais

**Fluxo em sentido único.** Dados só andam para frente (raw → bronze → silver → gold). Nenhuma etapa escreve de volta em camada anterior e nada pula camada (a ingestão nunca grava direto no bronze; a carga nunca grava direto no silver). Quebrar essa regra destrói a rastreabilidade — saber de onde cada número veio.

**Snapshots, não sobrescrita, no raw.** A fonte só expõe o estado atual; o histórico nasce do acúmulo de snapshots com `ingestao_ts`. Sobrescrever o raw eliminaria a única memória do que a fonte dizia em cada momento.

**Separação entre transformação e orquestração.** As procedures transformam; o Data Factory dispara tudo na ordem certa e lida com falhas. São responsabilidades distintas: ingestão raw → carga bronze → procedures do silver → procedures do gold, num pipeline com dependências.

**Idempotência.** Toda carga deve poder rodar duas vezes sem duplicar dados. A marca-d'água garante isso na carga bronze; cada procedure deixa a camada de destino no estado correto independente de quantas execuções aconteçam — seja recriando os dados, seja atualizando de forma incremental.

**Permissões por schema.** Schemas permitem controle de acesso real: o usuário do Power BI recebe leitura apenas no gold, garantindo que ninguém consuma dado cru por engano. A separação deixa de ser convenção de nome e vira barreira efetiva.

## 6. Convenções sugeridas

| Item | Convenção | Exemplo |
|---|---|---|
| Collection raw | nome da fonte | `raw_chuvas_apac` |
| Tabela bronze | mesmo nome da fonte | `bronze.chuvas_apac` |
| Tabela silver | mesmo nome, limpa | `silver.chuvas_apac` |
| Tabela gold | nome da pergunta de negócio | `gold.acumulado_semanal_bacia` |
| Procedure de carga | prefixo `carga_` no schema de destino | `silver.carga_chuvas_apac` |
| Tabela de controle | schema bronze | `bronze.controle_carga` (pipeline, ultimo_ts) |

## 7. Próximos passos possíveis

1. Criar o cluster M0 no Atlas e a collection raw.
2. Criar os schemas e as tabelas de cada camada no banco atual (incluindo `bronze.controle_carga`).
3. Montar a Pipeline 1 (ingestão API → Mongo) no Data Factory e escolher a frequência.
4. Montar a Pipeline 2 (Mongo → bronze) com o mecanismo de marca-d'água.
5. Escrever as procedures do silver (limpeza) e do gold (agregação).
6. Encadear tudo no Data Factory com dependências e retry.
7. Configurar permissões de leitura no gold para o Power BI.