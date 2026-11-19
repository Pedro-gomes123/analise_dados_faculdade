"""Processador silver: bronze.inmet_estacoes → silver.Estacoes."""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _upsert

logger = logging.getLogger(__name__)

_MERGE_EST = """\
MERGE silver.Estacoes WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (fonte, estacao, nome, municipio, latitude, longitude, situacao, atualizado_em)
ON  tgt.fonte   = src.fonte
AND tgt.estacao = src.estacao
WHEN NOT MATCHED THEN
    INSERT (fonte, estacao, nome, municipio, latitude, longitude, situacao, atualizado_em)
    VALUES (src.fonte, src.estacao, src.nome, src.municipio, src.latitude, src.longitude,
            src.situacao, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET
    nome          = src.nome,
    municipio     = src.municipio,
    latitude      = src.latitude,
    longitude     = src.longitude,
    situacao      = src.situacao,
    atualizado_em = src.atualizado_em;
"""


def _para_float(valor) -> float | None:
    """Converte string ou número para float.

    Necessário porque payloads brutos do INMET têm VL_LATITUDE como string.
    """
    if valor is None:
        return None
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def processar_estacoes(connection) -> dict:
    """Transforma metadados de estações INMET do bronze para silver.Estacoes.

    Suporta dois formatos de payload: normalizado (estacao, latitude) e
    bruto INMET (CD_ESTACAO, VL_LATITUDE). A cadeia de `or` cobre ambos.
    """
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.inmet_estacoes"):
        estacao = p.get("estacao") or p.get("CD_ESTACAO") or p.get("CD_WSI") or ""
        if not estacao:
            continue
        nome = p.get("nome") or p.get("DC_NOME")
        municipio = (
            p.get("municipio")
            or p.get("NM_MUNICIPIO")
            or p.get("DC_MUNICIPIO")
            or p.get("SG_ESTADO")
        )
        lat = _para_float(p.get("latitude") or p.get("VL_LATITUDE"))
        lon = _para_float(p.get("longitude") or p.get("VL_LONGITUDE"))
        situacao = p.get("situacao") or p.get("CD_SITUACAO")
        params.append((
            p.get("fonte") or "inmet",
            estacao,
            nome,
            municipio,
            lat,
            lon,
            situacao,
            agora,
        ))

    inseridos = _upsert(connection, "silver.Estacoes", _MERGE_EST, params)
    logger.info("silver.Estacoes: %d linhas processadas", inseridos)
    return {"tabela": "silver.Estacoes", "processados": inseridos}
