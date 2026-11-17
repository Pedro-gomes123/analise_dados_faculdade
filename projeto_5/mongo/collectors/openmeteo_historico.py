"""Coleta série horária histórica longa via Open-Meteo Archive (ERA5 Reanalysis).

Por que ERA5 Archive como complemento ao Forecast?
- O Open-Meteo Forecast cobre apenas 7 dias de histórico. Para análise
  de sazonalidade, comparação com períodos anteriores ou cargas iniciais
  de dados, precisamos de janelas maiores.
- ERA5 (ECMWF Reanalysis v5) é a referência global de reanálise climática:
  cobre desde 1940, resolução horária, disponível gratuitamente via API.
- Endpoint separado (archive-api.open-meteo.com) com delay de ~5 dias.
"""

import logging
from datetime import date, timedelta

from mongo.config import LAT, LON
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import get, para_numero, salvar_json_local, utc_datetime

logger = logging.getLogger(__name__)

# URL base do endpoint de arquivo histórico — diferente do endpoint de forecast.
OPENMETEO_ARCHIVE_BASE = "https://archive-api.open-meteo.com/v1/archive"

# Identificador da estação virtual. Inclui "archive" para distinguir da
# estação do forecast nas tabelas bronze e silver.
ESTACAO_ARCHIVE = f"openmeteo_archive_{LAT:.4f}_{LON:.4f}"

# Janela de coleta: 90 dias de histórico por execução.
# 90 dias cobre uma estação do ano completa e é suficiente para análise
# de tendências sazonais. Aumentar esse valor aumenta o tempo de resposta da API.
_DIAS_HISTORICO = 90


def pipeline_openmeteo_historico(db):
    """Baixa os últimos 90 dias de ERA5 reanalysis para Recife e persiste no MongoDB.

    Por que delay de 5 dias?
    A ERA5 é calculada offline por modelos de reanálise — os dados mais recentes
    ficam disponíveis com ~5 dias de atraso. Solicitar dados mais recentes retorna
    erro 400 ou resposta vazia. O delay protege contra esse caso.

    Por que natureza_dado = "reanalisado_era5"?
    ERA5 não é medição de estação nem previsão — é uma reanálise que combina
    observações históricas com modelos para reconstruir o estado da atmosfera.
    Ter um nome próprio permite que o app filtre ou pondere diferentemente.
    """
    logger.info("Iniciando pipeline Open-Meteo Archive (ERA5)")

    # Calcula a janela: de (hoje - 90 dias) até (hoje - 5 dias).
    # date.today() retorna a data local do servidor (sem tz), suficiente aqui.
    fim = date.today() - timedelta(days=5)       # -5 dias: delay de publicação ERA5
    inicio = fim - timedelta(days=_DIAS_HISTORICO - 1)

    resposta = get(
        OPENMETEO_ARCHIVE_BASE,
        params={
            "latitude": LAT,
            "longitude": LON,
            "start_date": inicio.isoformat(),   # formato YYYY-MM-DD exigido pela API
            "end_date": fim.isoformat(),
            # wind_speed_10m incluído aqui mas ausente no forecast:
            # o Archive tem mais variáveis disponíveis para análise histórica.
            "hourly": "precipitation,temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m",
            "timezone": "UTC",
        },
    )
    dados = resposta.json()
    salvar_json_local("openmeteo_archive", dados)

    if not isinstance(dados, dict) or not isinstance(dados.get("hourly"), dict):
        raise RuntimeError("Open-Meteo Archive retornou resposta sem bloco hourly válido.")

    hourly = dados["hourly"]
    tempos = hourly.get("time") or []
    if not tempos:
        raise RuntimeError("Open-Meteo Archive não retornou horários para o período solicitado.")

    # Mapeamento de variáveis — mesmo padrão do Forecast com adição de vento.
    nomes = {
        "precipitacao_mm": "precipitation",
        "temperatura_c": "temperature_2m",
        "umidade_pct": "relative_humidity_2m",
        "pressao_hpa": "surface_pressure",
        "vento_ms": "wind_speed_10m",   # vento em m/s a 10 m de altura
    }

    registros = []
    for indice, tempo in enumerate(tempos):
        lida_em = utc_datetime(tempo)
        if lida_em is None:
            logger.warning("Horário Archive inválido ignorado: %r", tempo)
            continue

        medidas = {
            campo: para_numero(
                hourly.get(chave, [])[indice]
                if indice < len(hourly.get(chave, []))
                else None
            )
            for campo, chave in nomes.items()
        }

        registros.append(
            {
                "fonte": "openmeteo_archive",
                "estacao": ESTACAO_ARCHIVE,
                "territorio": "Recife",
                "lida_em": lida_em,
                "natureza_dado": "reanalisado_era5",  # indica origem ERA5 ao app
                "variaveis": medidas,
                "unidades": dados.get("hourly_units", {}),
                "latitude": dados.get("latitude"),
                "longitude": dados.get("longitude"),
                "elevacao_m": dados.get("elevation"),
            }
        )

    if not registros:
        raise RuntimeError("Open-Meteo Archive não retornou horários válidos para persistência.")

    # A chave (estacao, lida_em) garante idempotência: re-executar com a mesma
    # janela de datas atualiza os documentos existentes sem criar duplicatas.
    # Isso permite corrigir dados de reanálise se a ERA5 for republicada.
    carregar_documentos(
        db["openmeteo_historico"],
        "openmeteo_archive",
        registros,
        "meteorologia_horaria_era5",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline Open-Meteo Archive concluído: %d horários", len(registros))
