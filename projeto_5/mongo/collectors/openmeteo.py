"""Coleta série horária de previsão e histórico modelado do Open-Meteo Forecast.

Por que Open-Meteo Forecast?
- API gratuita (10.000 req/dia sem token), confiável e amplamente usada.
- Fornece previsão e histórico recente (7 dias) no mesmo endpoint,
  o que cobre alertas em tempo real e análise dos últimos dias.
- Dados "passados" são calculados por modelo ERA5 downscaled — não são
  medições de estação física, mas têm boa correlação com observações reais.
"""

import logging
from datetime import datetime, timezone

# LAT/LON: coordenadas do ponto central de Recife (definidas em config.py)
from mongo.config import LAT, LON
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import get, para_numero, salvar_json_local, utc_datetime

logger = logging.getLogger(__name__)

# Identificador da estação virtual criado a partir das coordenadas.
# Usar lat/lon no nome torna o ID auto-descritivo e único para cada ponto
# geográfico — se adicionarmos outra cidade, o ID não colide.
ESTACAO_OPENMETEO = f"recife_{LAT:.4f}_{LON:.4f}"


def pipeline_openmeteo(db):
    """Coleta série horária do Open-Meteo Forecast e persiste no MongoDB.

    Decisões de design:
    - past_days=7: cobre uma semana de histórico para análise de tendência.
    - forecast_days=1: apenas o próximo dia — suficiente para alertas imediatos.
    - timezone=UTC: padroniza timestamps em UTC para consistência com as demais fontes.
    - natureza_dado: distingue "previsao" (futuro) de "historico_modelado" (passado
      calculado por modelo), pois têm confiabilidade diferente para o app.
    """
    logger.info("Iniciando pipeline Open-Meteo")

    # Parâmetros da requisição à API Open-Meteo Forecast.
    # "hourly" lista as variáveis desejadas separadas por vírgula.
    parametros = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": (
            "precipitation,temperature_2m,relative_humidity_2m,surface_pressure"
        ),
        "past_days": 7,       # histórico: 7 dias para análise de tendência
        "forecast_days": 1,   # previsão: 1 dia para alertas imediatos
        "timezone": "UTC",    # garante timestamps em UTC (padrão do projeto)
    }
    resposta = get("https://api.open-meteo.com/v1/forecast", params=parametros)
    dados = resposta.json()

    # Validação defensiva: a API pode retornar erro JSON sem levantar HTTPError.
    if not isinstance(dados, dict) or not isinstance(dados.get("hourly"), dict):
        raise RuntimeError("Open-Meteo retornou resposta sem bloco hourly válido.")
    salvar_json_local("openmeteo", dados)

    hourly = dados["hourly"]
    tempos = hourly.get("time") or []
    if not isinstance(tempos, list) or not tempos:
        raise RuntimeError("Open-Meteo não retornou horários para a série hourly.")

    # Mapeamento entre nome interno do projeto e nome da variável na API.
    # Manter esse dict isolado facilita adicionar novas variáveis sem
    # refatorar o loop principal.
    nomes = {
        "precipitacao_mm": "precipitation",
        "temperatura_c": "temperature_2m",
        "umidade_pct": "relative_humidity_2m",
        "pressao_hpa": "surface_pressure",
    }

    agora = datetime.now(timezone.utc)
    registros = []

    for indice, tempo in enumerate(tempos):
        # utc_datetime converte a string ISO 8601 da API para datetime Python com tz.
        lida_em = utc_datetime(tempo)
        if lida_em is None:
            logger.warning("Horário Open-Meteo inválido ignorado: %r", tempo)
            continue

        # para_numero: converte float da API para Python, tratando None e NaN.
        # O slice com verificação de índice evita IndexError se a API retornar
        # listas de tamanhos diferentes (caso de resposta parcial).
        medidas = {
            campo: para_numero(
                hourly.get(chave, [])[indice]
                if indice < len(hourly.get(chave, []))
                else None
            )
            for campo, chave in nomes.items()
        }

        # Classifica a natureza do dado: o mesmo endpoint retorna passado (modelo)
        # e futuro (previsão). A distinção importa para o app de alertas, que trata
        # "historico_modelado" com maior confiança que "previsao".
        natureza = "previsao" if lida_em > agora else "historico_modelado"

        registros.append(
            {
                "fonte": "openmeteo",
                "estacao": ESTACAO_OPENMETEO,
                "territorio": "Recife",
                "lida_em": lida_em,
                "natureza_dado": natureza,
                "variaveis": medidas,
                # unidades armazenadas para rastreabilidade (°C, mm, %, hPa)
                "unidades": dados.get("hourly_units", {}),
                "latitude": dados.get("latitude"),
                "longitude": dados.get("longitude"),
                "elevacao_m": dados.get("elevation"),
                "timezone_origem": dados.get("timezone"),
                # valores_originais: mantém o dado bruto da API para auditoria,
                # mesmo que medidas já tenha passado por para_numero().
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

    # campos_chave=(estacao, lida_em): o par estação + hora identifica de forma
    # única cada medição. O SHA-256 calculado sobre esses dois campos garante
    # que re-execuções do pipeline atualizem o documento sem criar duplicatas.
    carregar_documentos(
        db["openmeteo_horario"],
        "openmeteo",
        registros,
        "meteorologia_horaria",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline Open-Meteo concluído: %d horários", len(registros))
