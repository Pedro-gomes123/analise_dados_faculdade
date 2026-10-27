"""Coleta de dados meteorológicos do Open-Meteo."""

from src.config import LAT, LON
from src.database.mongodb import carregar_documentos
from src.utils.helpers import get, salvar_json_local


def pipeline_openmeteo(db):
    print("\n========== PIPELINE OPEN-METEO ==========")

    parametros = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": (
            "precipitation,"
            "temperature_2m,"
            "relative_humidity_2m,"
            "surface_pressure"
        ),
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "America/Recife",
    }

    resposta = get(
        "https://api.open-meteo.com/v1/forecast",
        params=parametros,
    )

    dados = resposta.json()

    salvar_json_local("openmeteo", dados)

    hourly = dados.get("hourly", {})
    tempos = hourly.get("time", [])

    chuva = hourly.get("precipitation", [])
    temperatura = hourly.get("temperature_2m", [])
    umidade = hourly.get("relative_humidity_2m", [])
    pressao = hourly.get("surface_pressure", [])

    registros = []

    for i, tempo in enumerate(tempos):
        registro = {
            "data_hora": tempo,
            "latitude": dados.get("latitude"),
            "longitude": dados.get("longitude"),
            "timezone": dados.get("timezone"),
            "precipitacao_mm": (
                chuva[i] if i < len(chuva) else None
            ),
            "temperatura_C": (
                temperatura[i] if i < len(temperatura) else None
            ),
            "umidade_pct": (
                umidade[i] if i < len(umidade) else None
            ),
            "pressao_hPa": (
                pressao[i] if i < len(pressao) else None
            ),
        }

        inicio_24 = max(0, i - 23)
        inicio_72 = max(0, i - 71)

        registro["chuva_24h_mm"] = (
            sum(
                valor
                for valor in chuva[inicio_24:i + 1]
                if valor is not None
            )
            if chuva
            else None
        )

        registro["chuva_72h_mm"] = (
            sum(
                valor
                for valor in chuva[inicio_72:i + 1]
                if valor is not None
            )
            if chuva
            else None
        )

        registros.append(registro)

    carregar_documentos(
        db["openmeteo_horario"],
        "open_meteo",
        registros,
        "meteorologia_horaria",
    )