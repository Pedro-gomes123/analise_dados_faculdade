# CRISP-DM — Projeto 5

## 1. Entendimento do Negócio

Buscamos resolver a **dispersão dos dados meteorológicos, hidrológicos, epidemiológicos, ambientais, assistenciais e territoriais**, possibilitando o cruzamento dessas informações para realizar análises e desenvolver modelos de **predição de desastres, possíveis epidemias e controle de riscos**.

A solução tem como objetivo reduzir os seguintes problemas:

- Elevado tempo gasto na consolidação manual de informações;
- Retrabalho das equipes técnicas;
- Dificuldade para identificar rapidamente áreas prioritárias de intervenção;
- Menor agilidade na produção de boletins, notas técnicas e relatórios;
- Limitação na geração de indicadores estratégicos.

---

## 2. Entendimento dos Dados

Serão utilizadas APIs e fontes de dados públicos relacionadas aos diferentes domínios necessários para a análise:

| Domínio | Fontes de dados |
|---|---|
| **Meteorológicos** | APAC / INMET |
| **Hidrológicos** | APAC / ANA |
| **Epidemiológicos** | Dados Abertos Recife / Secretaria de Saúde |
| **Ambientais** | CPRH / MonitorAr |
| **Assistenciais** | Dados Abertos Recife / DATASUS |
| **Territoriais** | COP Recife / Dados Abertos Recife |

Nessa etapa serão analisadas as características das fontes, como:

- Disponibilidade dos dados;
- Estrutura;
- Periodicidade de atualização;
- Dados históricos;
- Localização geográfica;
- Qualidade dos dados;
- Disponibilidade de APIs.

---

## 3. Preparação dos Dados

A coleta dos dados será realizada por meio das **APIs disponíveis e demais fontes públicas**, realizando a extração e o armazenamento dos dados inicialmente em uma camada **Raw**, preservando os dados em seu formato original.

Posteriormente, os dados serão convertidos para **Delta Tables** e armazenados na camada **Bronze**.

Na camada **Silver**, serão realizadas as tratativas necessárias, como:

- Normalização dos dados;
- Padronização dos campos;
- Tratamento de valores nulos;
- Exclusão de duplicidades;
- Padronização de datas e horários;
- Tratamento de inconsistências;
- Padronização das informações territoriais;
- Outras regras necessárias para garantir a qualidade dos dados.

Após o tratamento, os dados estarão preparados para os cruzamentos e análises na camada **Gold**.

### Fluxo de preparação

```text
APIs / Fontes Públicas
        ↓
       RAW
        ↓
  Delta Tables
        ↓
     BRONZE
        ↓
Tratamento dos Dados
        ↓
     SILVER
        ↓
Cruzamentos e Regras
        ↓
      GOLD

    ---

##4. Modelagem

Inicialmente será realizada uma análise diagnóstica dos dados, buscando compreender o comportamento dos fenômenos ao longo do tempo.

Serão analisados aspectos como:

Sazonalidade;
Tendências;
Variações;
Principais acontecimentos;
Relações entre diferentes eventos;
Comportamento histórico das ocorrências.

Após a análise diagnóstica, os diferentes conjuntos de dados serão cruzados para identificar padrões e relações entre os fenômenos meteorológicos, hidrológicos, epidemiológicos, ambientais, assistenciais e territoriais.

A partir dos padrões identificados, serão desenvolvidos modelos preditivos capazes de estimar a probabilidade de ocorrência de determinados eventos futuros.

Dessa forma, a solução poderá auxiliar na identificação antecipada de possíveis situações de risco, permitindo que as equipes tenham informações para agir preventivamente.

Fluxo da Modelagem
Dados Históricos
       ↓
Análise Diagnóstica
       ↓
Sazonalidade e Tendências
       ↓
Principais Acontecimentos
       ↓
Cruzamento dos Dados
       ↓
Identificação de Padrões
       ↓
Modelos Preditivos
       ↓
Estimativa de Possíveis Eventos
5. Avaliação

Nesta etapa serão avaliados os resultados obtidos a partir das análises e dos modelos desenvolvidos, verificando se eles são capazes de atender aos objetivos definidos na etapa de entendimento do negócio.

Serão avaliados aspectos como:

Qualidade dos resultados;
Consistência dos padrões identificados;
Desempenho dos modelos preditivos;
Capacidade de identificar situações de risco;
Precisão das previsões;
Comparação entre eventos previstos e eventos observados;
Utilidade dos resultados para as equipes técnicas.
6. Implantação

Os resultados obtidos serão disponibilizados por meio de um dashboard de monitoramento, permitindo a visualização integrada dos principais indicadores, eventos e áreas de risco.

Além do dashboard, será implementado um sistema de alertas preditivos, responsável por identificar situações com maior probabilidade de ocorrência a partir dos padrões encontrados pelos modelos.

A solução permitirá:

Monitorar os principais indicadores;
Visualizar áreas prioritárias;
Acompanhar possíveis situações de risco;
Receber alertas preditivos;
Apoiar a tomada de decisão das equipes;
Agilizar a produção de informações estratégicas.
Fluxo de Implantação
                    GOLD
                      ↓
             Modelos Preditivos
                      ↓
          ┌───────────┴───────────┐
          ↓                       ↓
      Dashboard           Alertas Preditivos
          ↓                       ↓
     Visualização             Notificação
          └───────────┬───────────┘
                      ↓
             Tomada de Decisão