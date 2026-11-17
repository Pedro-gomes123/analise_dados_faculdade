# Referência das APIs — VigiaClima Recife

> Documento gerado em 2026-11-15. Atualizar sempre que uma API for adicionada, removida ou tiver parâmetros alterados.

## Índice

1. [Open-Meteo Forecast](#1-open-meteo-forecast)
2. [Open-Meteo Archive ERA5](#2-open-meteo-archive-era5)
3. [NASA POWER Reanalysis](#3-nasa-power-reanalysis)
4. [CKAN Recife — Arboviroses](#4-ckan-recife--arboviroses)
5. [CKAN Recife — Defesa Civil](#5-ckan-recife--defesa-civil)
6. [PySUS / SINAN ANIM](#6-pysus--sinan-anim)
7. [INMET — Estações Automáticas](#7-inmet--estaes-automticas) *(metadados apenas)*

---

## Padrões comuns

| Padrão | Descrição |
|---|---|
| **Autenticação** | Nenhuma das APIs ativas exige token. O INMET exige token para observações (desativado). |
| **Fuso horário** | Todos os timestamps são armazenados em UTC com offset `+00:00`. |
| **Chave de idempotência** | SHA-256 gerado sobre os campos de negócio do documento (ver `mongo/database/mongodb.py`). |
| **Formato de período** | Semana ISO: `YYYY-WNN` (ex.: `2026-W46`). Mês: `YYYY-MM`. |
| **Sentinela de ausência** | NASA POWER usa `-999.0`; os demais retornam `null`/`None`. |

---

## 1. Open-Meteo Forecast

**Fonte no banco:** `openmeteo`  
**Coleção MongoDB:** `openmeteo_horario`  
**Tabela Bronze:** `bronze.openmeteo_horario`  
**Arquivo:** `mongo/collectors/openmeteo.py`

### Descrição

API de previsão do tempo com histórico de modelo ERA5 downscaled para qualquer ponto do globo. Gratuita até 10.000 req/dia. Não requer cadastro.

### Endpoint

```
GET https://api.open-meteo.com/v1/forecast
```

### Parâmetros utilizados

| Parâmetro | Valor configurado | Descrição |
|---|---|---|
| `latitude` | `-8.0476` | Latitude do ponto (Recife) |
| `longitude` | `-34.8770` | Longitude do ponto (Recife) |
| `hourly` | `precipitation,temperature_2m,relative_humidity_2m,surface_pressure` | Variáveis horárias solicitadas |
| `past_days` | `7` | Histórico dos últimos 7 dias (dados modelados) |
| `forecast_days` | `1` | Previsão para 1 dia à frente |
| `timezone` | `UTC` | Fuso horário da série retornada |

### Variáveis retornadas

| Campo API | Campo interno | Unidade | Descrição |
|---|---|---|---|
| `temperature_2m` | `temperatura_c` | °C | Temperatura do ar a 2 m |
| `precipitation` | `precipitacao_mm` | mm/h | Precipitação horária |
| `relative_humidity_2m` | `umidade_pct` | % | Umidade relativa a 2 m |
| `surface_pressure` | `pressao_hpa` | hPa | Pressão ao nível da superfície |

### Campo `natureza_dado`

- `"previsao"` — `lida_em > agora` (horário futuro)
- `"historico_modelado"` — `lida_em <= agora` (passado, mas calculado por modelo, não medido)

### Estrutura do payload armazenado

```json
{
  "fonte": "openmeteo",
  "estacao": "recife_-8.0476_-34.8770",
  "territorio": "Recife",
  "lida_em": "2026-11-15T12:00:00+00:00",
  "natureza_dado": "historico_modelado",
  "variaveis": {
    "precipitacao_mm": 0.5,
    "temperatura_c": 28.0,
    "umidade_pct": 80.0,
    "pressao_hpa": 1013.0
  },
  "latitude": -8.0476,
  "longitude": -34.8770,
  "elevacao_m": 7.0
}
```

### Limitações

- Histórico disponível: apenas **7 dias** passados no modo forecast; use o Archive (item 2) para histórico mais longo.
- Os dados "passados" são interpolação de modelo, não medições de estação física.
- Limite de requisições: 10.000/dia sem token; acima disso, disponível plano pago.

---

## 2. Open-Meteo Archive ERA5

**Fonte no banco:** `openmeteo_archive`  
**Coleção MongoDB:** `openmeteo_historico`  
**Tabela Bronze:** `bronze.openmeteo_historico`  
**Arquivo:** `mongo/collectors/openmeteo_historico.py`

### Descrição

API de arquivo histórico baseada na reanálise ERA5 do ECMWF. Permite consultar décadas de dados climáticos horários com delay de ~5 dias. Gratuita, sem cadastro.

### Endpoint

```
GET https://archive-api.open-meteo.com/v1/archive
```

### Parâmetros utilizados

| Parâmetro | Valor | Descrição |
|---|---|---|
| `latitude` | `-8.0476` | Latitude do ponto |
| `longitude` | `-34.8770` | Longitude do ponto |
| `start_date` | `hoje - 95 dias` | Início da janela histórica |
| `end_date` | `hoje - 5 dias` | Fim (delay de 5 dias para publicação) |
| `hourly` | `precipitation,temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m` | Inclui vento (ausente no forecast) |
| `timezone` | `UTC` | |

### Variáveis adicionais em relação ao forecast

| Campo API | Campo interno | Unidade |
|---|---|---|
| `wind_speed_10m` | `vento_ms` | m/s |

### Campo `natureza_dado`

Sempre `"reanalisado_era5"` — dados de reanálise, não previsão.

### Limitações

- **Delay de ~5 dias**: dados mais recentes ainda não estão publicados.
- Janela coletada a cada execução: **90 dias** (configurável em `_DIAS_HISTORICO`).
- Chave de idempotência: `(estacao, lida_em)` — re-execuções não duplicam dados.

---

## 3. NASA POWER Reanalysis

**Fonte no banco:** `nasa_power`  
**Coleção MongoDB:** `nasa_power_horario`  
**Tabela Bronze:** `bronze.nasa_power_horario`  
**Arquivo:** `mongo/collectors/nasa_power.py`

### Descrição

API gratuita da NASA que fornece dados climáticos reanalisados (MERRA-2) para qualquer ponto do globo. Delay de ~1 dia. Sem cadastro ou token.

### Endpoint

```
GET https://power.larc.nasa.gov/api/temporal/hourly/point
```

### Parâmetros utilizados

| Parâmetro | Valor | Descrição |
|---|---|---|
| `parameters` | `T2M,PRECTOTCORR,RH2M,PS,WS2M` | Variáveis solicitadas (ver tabela abaixo) |
| `community` | `RE` | Renewable Energy — timestamps em UTC |
| `longitude` | `-34.8770` | |
| `latitude` | `-8.0476` | |
| `start` | `YYYYMMDD` (hoje - 30 dias) | |
| `end` | `YYYYMMDD` (hoje - 1 dia) | Delay de 1 dia |
| `format` | `JSON` | |

### Variáveis e mapeamento

| Código NASA | Campo interno | Unidade original | Unidade armazenada |
|---|---|---|---|
| `T2M` | `temperatura_c` | °C | °C |
| `PRECTOTCORR` | `precipitacao_mm` | mm/h | mm/h |
| `RH2M` | `umidade_pct` | % | % |
| `PS` | `pressao_kpa` | **kPa** | kPa (convertido para hPa × 10 na camada silver) |
| `WS2M` | `vento_ms` | m/s | m/s |

> **Atenção:** Pressão é armazenada em **kPa** no bronze/MongoDB. A conversão para hPa (× 10) ocorre em `silver/pipelines/silver_pipeline.py` → `_linha_meteorologia`.

### Formato das chaves de tempo

A API retorna dicionários com chaves no formato `YYYYMMDDH` (10 caracteres numéricos: 8 de data + 2 de hora). Exemplo: `"2026111512"` = 2026-11-15 12:00 UTC.

### Sentinela de dado ausente

Valor `-999.0` indica ausência de dado. Convertido para `None` em `_valor_ou_none`.

### Campo `natureza_dado`

Sempre `"reanalisado"` — reanálise MERRA-2, não medição direta.

### Limitações

- Janela coletada: **30 dias** (delay de 1 dia).
- Pressão em kPa requer conversão manual para hPa.
- Resolução espacial: ~0,5° × 0,625° (grade global MERRA-2).

---

## 4. CKAN Recife — Arboviroses

**Fonte no banco:** `dados_abertos_recife`  
**Coleção MongoDB:** `recife_arboviroses`  
**Tabela Bronze:** `bronze.recife_arboviroses`  
**Arquivo:** `mongo/collectors/recife.py`

### Descrição

Portal de dados abertos da Prefeitura do Recife (CKAN). Fornece notificações de dengue, zika e chikungunya com granularidade de bairro e semana epidemiológica. Os dados individuais são **agregados por bairro/semana** antes do armazenamento (LGPD).

### Endpoints utilizados

```
GET https://dados.recife.pe.gov.br/api/3/action/package_search
    ?q=dengue+zika+chikungunya&rows=50

GET {url_recurso}   (CSV ou JSON do dataset encontrado)
```

### Mapeamento de agravos (IDs CID-10)

| Código | Agravo interno |
|---|---|
| `A90`, `A91` | `dengue` |
| `A92.0` | `chikungunya` |
| `U06.9` | `zika` |

### Campo `periodo`

Semana ISO 8601: `YYYY-WNN`.  
Derivado de (em ordem de prioridade): `SEM_NOT` → `SEM_PRI` → `DT_NOTIFIC`.

### Dados armazenados (apenas agregados)

```json
{
  "territorio": "Recife",
  "bairro": "Boa Viagem",
  "indicador": "dengue",
  "periodo": "2026-W44",
  "valor": 12
}
```

Nenhum dado individual (nome, CPF, endereço) é persistido.

### Limitações

- Dataset depende de publicação periódica pela Secretaria de Saúde do Recife.
- O pipeline procura recursos CSV/JSON com campos de bairro e semana; se o schema do arquivo mudar, pode não encontrar dados válidos.
- Histórico completo disponível no portal (anos anteriores).

---

## 5. CKAN Recife — Defesa Civil

**Fonte no banco:** `dados_abertos_recife`  
**Coleção MongoDB:** `recife_defesa_civil`  
**Tabela Bronze:** `bronze.recife_defesa_civil`  
**Arquivo:** `mongo/collectors/defesa_civil.py`

> **Substituiu:** `s2id.py` (dados.gov.br/S2ID), que passou a retornar HTTP 401 em 2026.

### Descrição

Atendimentos da Defesa Civil do Recife publicados no portal CKAN da Prefeitura. Inclui tipo de ocorrência (deslizamento, alagamento, incêndio, etc.), bairro e mês.

### Endpoints utilizados

```
GET https://dados.recife.pe.gov.br/api/3/action/package_show
    ?id=registro-de-atendimentos-da-defesa-civil

GET {url_csv}   (um CSV por ano; os 2 mais recentes são baixados)
```

### Colunas utilizadas do CSV

| Coluna CSV | Uso |
|---|---|
| `Ano` | Ano do atendimento |
| `Mês` | Mês por extenso em português (ex.: `novembro`) |
| `Ocorrencia` / `Solicitacao` | Tipo de ocorrência |
| `Bairro` | Bairro do atendimento |

### Dados armazenados (agregados mensais)

```json
{
  "territorio": "Recife",
  "bairro": "Afogados",
  "tipo_ocorrencia": "Deslizamento",
  "periodo": "2026-11",
  "valor": 3
}
```

### Limitações

- Dataset cobre apenas **Recife** (municipal).
- Os CSVs são publicados por ano; o coletor baixa os **2 anos mais recentes**.
- Deduplicação por nome de recurso: o portal por vezes republica o mesmo CSV.

---

## 6. PySUS / SINAN ANIM

**Fonte no banco:** `pysus_sinan`  
**Coleção MongoDB:** `sinan_animais_peconhentos`  
**Tabela Bronze:** `bronze.sinan_animais_peconhentos`  
**Arquivo:** `mongo/collectors/sinan.py`

### Descrição

Dados do Sistema de Informação de Agravos de Notificação (SINAN) para acidentes com animais peçonhentos (código ANIM). Acesso via biblioteca Python **PySUS**, que faz download do FTP do DATASUS.

### Acesso

```python
import pysus
df = pysus.ftp.sinan(disease="ANIM", year=2026, as_dataframe=True)
```

Sem token nem cadastro. Requer acesso à internet e a biblioteca `pysus` instalada.

### Lógica de ano

O pipeline tenta o **ano corrente** primeiro; se o arquivo ainda não foi publicado, recua para o **ano anterior**. Em 2026, o arquivo `ANIMBR26.parquet` estava disponível com 275.162 registros.

### Filtro geográfico

Apenas registros de **Pernambuco** (`SG_UF_NOT = "PE"` ou `SG_UF = "PE"`). Se a coluna de UF estiver ausente, o pipeline interrompe para evitar gravar dados nacionais como se fossem estaduais.

### Campo `periodo`

Semana ISO derivada de `SEM_NOT` ou `SEM_PRI`. Fallback para `DT_NOTIFIC`.

### Dados armazenados (agregados semanais por município)

```json
{
  "territorio": "Pernambuco",
  "municipio": "Recife",
  "codigo_municipio": "261160",
  "indicador": "acidentes_animais_peconhentos",
  "periodo": "2026-W44",
  "valor": 7
}
```

### Limitações

- Granularidade: **município** (não bairro). O SINAN ANIM não fornece bairro.
- Publicação anual: dados do ano corrente ficam disponíveis com meses de atraso.
- Volume alto: ~275 k registros para PE em 2026 — a leitura pode levar alguns segundos.

---

## 7. INMET — Estações Automáticas

**Fonte no banco:** `inmet`  
**Coleção MongoDB:** `inmet_estacoes`  
**Tabela Bronze:** `bronze.inmet_estacoes`  
**Arquivo:** `mongo/collectors/inmet.py` *(não ativo no pipeline principal)*

### Status atual

**Metadados de estações:** coletados sem token. Disponível em `bronze.inmet_estacoes` e `silver.Estacoes`.  
**Observações horárias:** requerem token (`INMET_TOKEN` no `.env`) e estão **desativadas** do pipeline principal por falta de token.

### Obter token

Acesse [portal.inmet.gov.br](https://portal.inmet.gov.br), crie uma conta e gere um token de API. Adicione ao `.env`:

```
INMET_TOKEN=seu_token_aqui
```

Reative o coletor em `mongo/main.py` descomentando `pipeline_inmet`.

### Endpoint de metadados (sem token)

```
GET https://apitempo.inmet.gov.br/estacoes/T
```

Retorna todas as estações automáticas do Brasil. O pipeline filtra por `SG_ESTADO = "PE"` (16 estações em Pernambuco).

### Endpoint de observações (requer token)

```
GET https://apitempo.inmet.gov.br/estacao/{inicio}/{fim}/{codigo}
    ?token={INMET_TOKEN}
```

| Parâmetro | Exemplo |
|---|---|
| `inicio` | `2026-11-13` |
| `fim` | `2026-11-15` |
| `codigo` | `A301` (Recife/PE) |

### Estação de referência para Recife

| Campo | Valor |
|---|---|
| Código | `A301` |
| Nome | RECIFE / PE |
| Latitude | -8.059 |
| Longitude | -34.950 |
| Altitude | 11 m |

### Variáveis das observações

| Campo INMET | Campo interno | Unidade |
|---|---|---|
| `CHUVA` / `PRECIPITACAO_TOTAL` | `precipitacao_mm` | mm/h |
| `TEMP_INS` / `TEM_INS` | `temperatura_c` | °C |
| `UMD_INS` / `UMID_REL` | `umidade_pct` | % |
| `PRE_INS` / `PRESSAO_ATMOSFERICA` | `pressao_hpa` | hPa |

### Campo `natureza_dado`

`"observado"` — medição real de estação física (diferente de modelo/reanálise).

---

## Variáveis de ambiente necessárias

Arquivo `.env` na raiz do projeto:

```dotenv
# Obrigatórias
MONGODB_URI=mongodb+srv://...
SQL_SERVER_HOST=bancosrv-proj5-dev.database.windows.net
SQL_SERVER_DATABASE=...
SQL_SERVER_USER=vigia_operator
SQL_SERVER_PASSWORD=...

# Opcionais
INMET_TOKEN=         # deixe vazio se não tiver token
LOG_LEVEL=INFO       # DEBUG para mais detalhe
```

---

## Dependências Python

```
# mongo/requirements.txt
requests
pymongo
pysus
pandas

# silver/requirements.txt  (reutilizadas pelo bronze e gold)
pymssql  ou  pyodbc
python-dotenv
pymongo   # para json_util (bson)
```
