"""Processador silver: bronze → silver.Meteorologia.

Unifica openmeteo_horario, openmeteo_historico e nasa_power_horario.
Normaliza pressão para hPa (NASA POWER envia kPa; conversão × 10).
"""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _ts, _upsert

logger = logging.getLogger(__name__)

_MERGE_MET = """\
MERGE silver.Meteorologia WITH (HOLDLOCK) AS tgt
USING (VALUES (
    ?, ?, ?,
    CONVERT(datetimeoffset(6), ?),
    ?, ?, ?, ?, ?, ?, ?, ?,
    CONVERT(datetimeoffset(6), ?)
)) AS src (fonte, estacao, territorio, lida_em, natureza_dado,
           temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
           vento_ms, latitude, longitude, atualizado_em)
ON tgt.fonte = src.fonte AND tgt.lida_em = src.lida_em
WHEN NOT MATCHED THEN
    INSERT (fonte, estacao, territorio, lida_em, natureza_dado,
            temperatura_c, precipitacao_mm, umidade_pct, pressao_hpa,
            vento_ms, latitude, longitude, atualizado_em)
    VALUES (src.fonte, src.estacao, src.territorio, src.lida_em, src.natureza_dado,
            src.temperatura_c, src.precipitacao_mm, src.umidade_pct, src.pressao_hpa,
            src.vento_ms, src.latitude, src.longitude, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    temperatura_c   = src.temperatura_c,
    precipitacao_mm = src.precipitacao_mm,
    umidade_pct     = src.umidade_pct,
    pressao_hpa     = src.pressao_hpa,
    vento_ms        = src.vento_ms,
    atualizado_em   = src.atualizado_em;
"""


def _linha_meteorologia(p: dict, agora: str) -> tuple | None:
    """Extrai e normaliza os campos de um payload de meteorologia.

    NASA POWER envia pressão em kPa; multiplica por 10 para converter para hPa.
    Retorna None se fonte ou lida_em estiverem ausentes (campos da chave de negócio).
    """
    variaveis = p.get("variaveis") or {}
    lida_em   = _ts(p.get("lida_em"))
    fonte     = p.get("fonte") or ""

    if not lida_em or not fonte:
        return None

    pressao = variaveis.get("pressao_hpa")
    if pressao is None and variaveis.get("pressao_kpa") is not None:
        pressao = variaveis["pressao_kpa"] * 10

    return (
        fonte,
        p.get("estacao") or "",
        p.get("territorio") or "Recife",
        lida_em,
        p.get("natureza_dado"),
        variaveis.get("temperatura_c"),
        variaveis.get("precipitacao_mm"),
        variaveis.get("umidade_pct"),
        pressao,
        variaveis.get("vento_ms"),
        p.get("latitude"),
        p.get("longitude"),
        agora,
    )


def processar_meteorologia(connection) -> dict:
    """Lê as três fontes climáticas do bronze e persiste em silver.Meteorologia."""
    agora = datetime.now(timezone.utc).isoformat()
    tabelas = [
        "bronze.openmeteo_horario",
        "bronze.openmeteo_historico",
        "bronze.nasa_power_horario",
    ]
    params = []
    for tabela in tabelas:
        for p in _ler_bronze(connection, tabela):
            linha = _linha_meteorologia(p, agora)
            if linha:
                params.append(linha)

    inseridos = _upsert(connection, "silver.Meteorologia", _MERGE_MET, params)
    logger.info("silver.Meteorologia: %d linhas processadas", inseridos)
    return {"tabela": "silver.Meteorologia", "processados": inseridos}
