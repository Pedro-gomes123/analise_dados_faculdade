"""Coleta série horária do Open-Meteo com instante UTC e variáveis comuns."""

import logging
from datetime import datetime, timezone

from mongo.config import LAT, LON
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import get, para_numero, salvar_json_local, utc_datetime

logger = logging.getLogger(__name__)
ESTACAO_OPENMETEO = f"recife_{LAT:.4f}_{LON:.4f}"


def pipeline_openmeteo(db):
    """Grava uma observação por ponto/hora, preservando valores e unidades."""
    logger.info("Iniciando pipeline Open-Meteo")
    parametros = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": (
            "precipitation,temperature_2m,relative_humidity_2m,surface_pressure"
        ),
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "UTC",
    }
    resposta = get("https://api.open-meteo.com/v1/forecast", params=parametros)
    dados = resposta.json()
    if not isinstance(dados, dict) or not isinstance(dados.get("hourly"), dict):
        raise RuntimeError("Open-Meteo retornou resposta sem bloco hourly válido.")
    salvar_json_local("openmeteo", dados)

    hourly = dados["hourly"]
    tempos = hourly.get("time") or []
    if not isinstance(tempos, list) or not tempos:
        raise RuntimeError("Open-Meteo não retornou horários para a série hourly.")

    nomes = {
        "precipitacao_mm": "precipitation",
        "temperatura_c": "temperature_2m",
        "umidade_pct": "relative_humidity_2m",
        "pressao_hpa": "surface_pressure",
    }
    agora = datetime.now(timezone.utc)
    registros = []
    for indice, tempo in enumerate(tempos):
        lida_em = utc_datetime(tempo)
        if lida_em is None:
            logger.warning("Horário Open-Meteo inválido ignorado: %r", tempo)
            continue
        medidas = {
            campo: para_numero(
                hourly.get(chave, [])[indice]
                if indice < len(hourly.get(chave, []))
                else None
            )
            for campo, chave in nomes.items()
        }
        # A API forecast pode fornecer valores anteriores por modelo; não os
        # rotulamos como observações medidas por estação.
        natureza = "previsao" if lida_em > agora else "historico_modelado"
        registros.append(
            {
                "fonte": "openmeteo",
                "estacao": ESTACAO_OPENMETEO,
                "territorio": "Recife",
                "lida_em": lida_em,
                "natureza_dado": natureza,
                "variaveis": medidas,
                "unidades": dados.get("hourly_units", {}),
                "latitude": dados.get("latitude"),
                "longitude": dados.get("longitude"),
                "elevacao_m": dados.get("elevation"),
                "timezone_origem": dados.get("timezone"),
                "valores_originais": {
                    chave: (hourly.get(chave) or [])[indice]
                    if indice < len(hourly.get(chave) or [])
                    else None
                    for chave in nomes.values()
                },
            }
        )

    if not registros:
        raise RuntimeError("Open-Meteo não retornou horários válidos para persistência.")
    carregar_documentos(
        db["openmeteo_horario"],
        "openmeteo",
        registros,
        "meteorologia_horaria",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline Open-Meteo concluído: %d horários", len(registros))
