"""Coleta dados climáticos horários reanalisados da API NASA POWER.

Por que NASA POWER como terceira fonte climática?
- É uma fonte independente da Open-Meteo — permite cruzar e validar leituras.
- Reanálise MERRA-2 (Modern-Era Retrospective analysis for Research and
  Applications): modelo da NASA com cobertura desde 1981, resolução horária.
- 100% gratuita, sem token, sem limite de requisições para uso acadêmico.
- O projeto usa três fontes climáticas (openmeteo, openmeteo_archive, nasa_power)
  para aumentar a robustez: se uma API sair do ar, as outras cobrem a lacuna.
"""

import logging
from datetime import date, timedelta

from mongo.config import LAT, LON
from mongo.database.mongodb import carregar_documentos
from mongo.utils.http import get
from mongo.utils.normalizers import para_numero, utc_datetime
from mongo.utils.storage import salvar_json_local

logger = logging.getLogger(__name__)

# Endpoint da API NASA POWER — versão temporal horária para um ponto (point).
NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/hourly/point"

# Variáveis solicitadas (códigos NASA POWER):
# T2M   = Temperature at 2 Meters (°C)
# PRECTOTCORR = Precipitation Corrected (mm/h)
# RH2M  = Relative Humidity at 2 Meters (%)
# PS    = Surface Pressure (kPa) — ATENÇÃO: kPa, não hPa como os demais
# WS2M  = Wind Speed at 2 Meters (m/s)
_PARAMETROS = "T2M,PRECTOTCORR,RH2M,PS,WS2M"

# Sentinela NASA POWER: valor -999.0 indica dado ausente no grid MERRA-2.
# Precisamos detectar isso explicitamente porque o JSON retorna o número,
# não null, quando a variável não está disponível para aquele ponto/horário.
_NASA_FILL = -999.0


def _valor_ou_none(v):
    """Retorna None para o sentinela NASA -999 e para NaN/inf.

    Dois níveis de verificação:
    1. para_numero() descarta strings não-numéricas e NaN/Inf.
    2. Comparação com _NASA_FILL descarta o sentinela de ausência da NASA.
    """
    n = para_numero(v)
    if n is None:
        return None
    # Sentinela NASA: -999 ou menor indica que o MERRA-2 não tem dado
    # para esse ponto e horário (ex: sobre oceano para variáveis terrestres).
    return None if n <= _NASA_FILL else n


def pipeline_nasa_power(db):
    """Baixa os últimos 30 dias horários do NASA POWER para Recife e persiste no MongoDB.

    Por que community="RE" (Renewable Energy)?
    A NASA POWER tem três "communities" com diferentes variáveis disponíveis.
    - RE (Renewable Energy): inclui todas as variáveis climáticas que usamos
      e retorna timestamps em UTC — essencial para consistência do projeto.
    - SB (Sustainable Buildings) e AG (Agroclimatology) não oferecem PS (pressão).

    Janela de 30 dias (delay de 1 dia):
    - O MERRA-2 é publicado com ~1 dia de atraso.
    - 30 dias cobre um mês completo para análise mensal.
    """
    logger.info("Iniciando pipeline NASA POWER")

    # Janela de coleta: hoje - 30 dias até ontem (delay de 1 dia do MERRA-2).
    fim = date.today() - timedelta(days=1)
    inicio = fim - timedelta(days=29)  # 30 dias totais (início incluído)

    resposta = get(
        NASA_POWER_BASE,
        params={
            "parameters": _PARAMETROS,
            "community": "RE",           # Renewable Energy: UTC + todas as vars
            "longitude": LON,
            "latitude": LAT,
            # NASA POWER usa formato YYYYMMDD (sem hífens) para as datas.
            "start": inicio.strftime("%Y%m%d"),
            "end": fim.strftime("%Y%m%d"),
            "format": "JSON",
        },
    )
    dados = resposta.json()
    salvar_json_local("nasa_power", dados)

    # A API pode retornar o bloco de parâmetros em dois locais dependendo
    # da versão: properties.parameter ou features[0].properties.parameter.
    # Tentamos ambos para robustez a mudanças de versão.
    parametros = (
        dados.get("properties", {}).get("parameter")
        or dados.get("features", [{}])[0].get("properties", {}).get("parameter")
    )
    if not parametros:
        raise RuntimeError("NASA POWER retornou resposta sem bloco 'parameter'.")

    # Extrai cada variável como um dict {chave_tempo: valor}.
    t2m  = parametros.get("T2M", {})       # temperatura 2m (°C)
    prec = parametros.get("PRECTOTCORR", {}) # precipitação corrigida (mm/h)
    rh2m = parametros.get("RH2M", {})       # umidade relativa 2m (%)
    ps   = parametros.get("PS", {})          # pressão superficial (kPa)
    ws2m = parametros.get("WS2M", {})        # vento 2m (m/s)

    registros = []
    for chave in sorted(t2m):
        # Formato das chaves de tempo NASA POWER: "YYYYMMDDH" (10 dígitos).
        # Exemplo: "2026111512" = 2026-11-15 12:00 UTC.
        # Versões antigas da API usavam underscore ("YYYYMMDD_HH") — replace() cobre ambos.
        chave_limpa = chave.replace("_", "")
        if len(chave_limpa) != 10 or not chave_limpa.isdigit():
            logger.warning("Chave de tempo NASA POWER inválida ignorada: %r", chave)
            continue

        # Reconstrói ISO 8601 a partir do formato compacto da NASA.
        # int(chave_limpa[8:]) converte "09" → 9 → f"{9:02d}" → "09" (preserva zero).
        iso = (
            f"{chave_limpa[:4]}-{chave_limpa[4:6]}-{chave_limpa[6:8]}"
            f"T{int(chave_limpa[8:]):02d}:00:00"
        )
        lida_em = utc_datetime(iso)
        if lida_em is None:
            continue

        registros.append(
            {
                "fonte": "nasa_power",
                "estacao": f"nasa_{LAT:.4f}_{LON:.4f}",
                "territorio": "Recife",
                "lida_em": lida_em,
                "natureza_dado": "reanalisado",  # MERRA-2: reanálise, não medição direta
                "variaveis": {
                    "temperatura_c":  _valor_ou_none(t2m.get(chave)),
                    "precipitacao_mm": _valor_ou_none(prec.get(chave)),
                    "umidade_pct":     _valor_ou_none(rh2m.get(chave)),
                    # IMPORTANTE: NASA POWER retorna pressão em kPa (não hPa).
                    # A conversão para hPa (× 10) é feita na camada silver para
                    # manter o dado bruto original no bronze/MongoDB.
                    "pressao_kpa":    _valor_ou_none(ps.get(chave)),
                    "vento_ms":       _valor_ou_none(ws2m.get(chave)),
                },
                # Unidades armazenadas para rastreabilidade e documentação.
                "unidades": {
                    "temperatura_c":  "C",
                    "precipitacao_mm": "mm/h",
                    "umidade_pct":     "%",
                    "pressao_kpa":    "kPa",   # atenção: kPa, não hPa
                    "vento_ms":       "m/s",
                },
                "latitude": LAT,
                "longitude": LON,
            }
        )

    if not registros:
        raise RuntimeError("NASA POWER não retornou horários válidos para persistência.")

    carregar_documentos(
        db["nasa_power_horario"],
        "nasa_power",
        registros,
        "meteorologia_horaria_reanalisada",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline NASA POWER concluído: %d horários", len(registros))
