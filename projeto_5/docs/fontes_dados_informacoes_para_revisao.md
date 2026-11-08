# Revisão das APIs do VigiaClima — informações necessárias

Este documento registra o que foi observado nas consultas somente de leitura de **6 de novembro de 2026** e reúne as decisões e amostras necessárias para ajustar os coletores Mongo. Nenhuma consulta desta revisão gravou dados no MongoDB.

## Resumo do diagnóstico

| Fonte | Situação observada | Próximo passo |
|---|---|---|
| INMET — catálogo de estações | HTTP 200; 668 estações, 16 em Pernambuco e A301 presente | Nenhuma informação adicional para localizar a estação |
| INMET — observações A301 | HTTP 204 sem conteúdo tanto para 2 como para 30 dias | Confirmar disponibilidade no portal e fornecer amostra/exportação para comparar rota, datas e campos |
| Open-Meteo | HTTP 200; série de 192 horários com as quatro variáveis climáticas | Confirmar ponto geográfico, nome do ponto e tipo de série histórica desejado |
| Dados Abertos Recife | CKAN HTTP 200; um dataset com 49 recursos em formatos suportados. O CSV de chikungunya 2025 foi lido e tinha 1.942 linhas | Confirmar período, significado dos casos e regra de semana/bairro; validar dengue e zika também |
| S2ID / dados.gov.br | CKAN retornou HTTP 401 | Fornecer a URL/ID do conjunto esperado ou confirmar se há autenticação/restrição na rede |
| SINAN / PySUS | Catálogo localizou um arquivo ANIM de 2025; a descarga integral não foi feita nesta revisão | Confirmar se a agregação deve ser para Recife ou Pernambuco e quais limites temporais usar |

## Informações por fonte

### 1. INMET — observações da A301

**O que já sabemos:** o catálogo da API responde e contém a estação A301. A rota de observações consultada retornou HTTP 204 para **7 de outubro a 6 de novembro de 2026**; a consulta original dos dois dias também não retornou conteúdo. O pipeline atual trata essa resposta vazia como conclusão normal, então pode parecer bem-sucedido sem ter gravado observações.

**Precisamos confirmar:**

- A estação desejada continua sendo `A301` (Recife/Curado)?
- No portal do INMET, aparecem observações da A301 para o período de 7/10 a 6/11/2026? Se sim, envie o CSV/JSON exportado ou uma captura das datas e dos nomes das colunas. Não precisa enviar credenciais.
- Se o portal também estiver vazio, qual estação próxima deve servir de contingência? Se não houver substituta, manter A301 e registrar ausência como dado indisponível.
- Qual o intervalo mínimo para considerar a fonte saudável: última hora, 24 h ou outro período?

**Campos a conferir na amostra:** identificador da estação, data e hora, chuva, temperatura, umidade e pressão. A amostra é necessária para confirmar os nomes reais e a unidade de cada campo, sem inferir nomes de colunas.

### 2. Open-Meteo

**O que já sabemos:** o endpoint atual retorna 192 horários e precipitação, temperatura, umidade relativa e pressão. A chamada usa o ponto configurado em `mongo/config.py` (`LAT`, `LON`), `timezone=UTC`, `past_days=7` e `forecast_days=1`.

Os valores passados de `/v1/forecast` com `past_days` são dados de previsão arquivados/modelados; não devem ser apresentados como leitura observada por uma estação. A documentação do Open-Meteo distingue essa série da API de histórico meteorológico `/v1/archive`. [Forecast API](https://open-meteo.com/en/docs), [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).

**Precisamos confirmar:**

- O ponto é o centro de Recife (`-8.05, -34.90`) ou deve coincidir com a A301?
- Qual rótulo estável usar para o ponto Open-Meteo (por exemplo, um código derivado das coordenadas)?
- Para o histórico, vocês querem reanálise/condições históricas da API Archive, previsões antigas arquivadas, ou apenas os sete dias recentes do endpoint atual? São produtos diferentes.
- Qual intervalo histórico inicial é necessário para o painel e comparação de períodos?

### 3. Dados Abertos Recife — arboviroses

**O que já sabemos:** a busca CKAN respondeu. A amostra do CSV de chikungunya 2025 continha campos de notificação, município, bairro, agravo e semana; a validação local reconheceu linhas de Recife para agregação. O coletor deve persistir somente contagens agregadas, nunca os dados individuais das notificações.

**Precisamos confirmar:**

- O painel deve contar **casos confirmados** ou todas as notificações? O recurso encontrado se chama “Casos confirmados de Chikungunya em 2025”.
- O período epidemiológico deve usar `SEM_NOT` (semana da notificação) ou `SEM_PRI` (semana dos primeiros sintomas)?
- Para os bairros, usar o bairro de residência (`NM_BAIRRO`) ou outra localização disponível na fonte?
- Qual período histórico deve ser carregado para dengue, zika e chikungunya?
- Devemos ignorar bairros ausentes ou agrupá-los como “não informado”?

Se houver uma definição de negócio oficial para “caso” ou semana epidemiológica, envie o documento ou a regra. Não precisamos de nomes, endereços ou linhas individuais.

### 4. S2ID / dados.gov.br

**O que já sabemos:** a busca CKAN usada pelo coletor respondeu HTTP 401; não foi possível listar os conjuntos. O coletor atual depende de localizar recursos CSV/JSON/XLSX com UF identificável antes de aceitar linhas de Pernambuco.

**Precisamos confirmar:**

- O portal `dados.gov.br` abre normalmente no seu navegador/rede?
- Qual é o link direto ou identificador do conjunto S2ID que vocês pretendem usar? Um link da página do conjunto já ajuda; não envie tokens ou senhas.
- O conjunto deve cobrir todo Pernambuco ou apenas Recife?
- Se a UF não vier como coluna, qual campo/código oficial identifica o município ou estado?
- Se existir autenticação institucional, informe apenas que ela é necessária e qual mecanismo deve ser usado. Credenciais devem ser configuradas localmente em variável de ambiente, nunca neste documento ou no chat.

### 5. SINAN / PySUS — acidentes por animais peçonhentos (ANIM)

**O que já sabemos:** o catálogo PySUS lista um arquivo do grupo ANIM para 2025. A extração completa desse arquivo não foi executada durante a revisão. Para proteger dados pessoais, o resultado final precisa ser agregado antes de ser persistido.

**Precisamos confirmar:**

- O recorte desejado é Recife ou todo Pernambuco? O requisito do painel aponta para Recife, mas a coleta atual consulta o arquivo nacional.
- Qual granularidade é útil: semana e município, ou outra agregação? A fonte pode não oferecer bairro utilizável.
- Quais anos devem entrar na carga histórica?
- Em caso de município sem nome, o código IBGE pode ser mantido para análise?

Não enviar nem solicitar planilhas com identificação de pacientes. Para validar a extração, basta compartilhar o schema (nomes/tipos de coluna), contagens por ano/UF/município e uma amostra sintética ou anonimizada.

## Resposta rápida

Para destravar os ajustes, responda copiando e preenchendo:

```text
INMET:
- A301 continua sendo a estação principal? (sim/não; substituta se houver)
- O portal mostra dados no período consultado? (sim/não/não verifiquei)
- Disponibilidade mínima esperada:

Open-Meteo:
- Coordenadas/ponto desejado:
- Histórico desejado (dias/anos e tipo: reanálise ou previsão arquivada):

Arboviroses Recife:
- Contar casos confirmados ou notificações:
- Usar semana de notificação ou de sintomas:
- Anos desejados:
- Bairro ausente: excluir ou agrupar como “não informado”:

S2ID:
- Link/ID do conjunto:
- Recife ou Pernambuco:
- Portal abre na minha rede? (sim/não/não verifiquei)

SINAN ANIM:
- Recorte: Recife ou Pernambuco:
- Granularidade:
- Anos desejados:
```

## Critério para retomar a gravação no Mongo

Primeiro confirmamos respostas, schemas e recortes acima. Depois validamos cada coletor com amostra controlada e resumo de contagens. A gravação no Mongo só é retomada após as fontes e filtros produzirem os dados esperados; falha HTTP, resposta vazia e fonte sem cobertura serão reportadas como estados diferentes.
