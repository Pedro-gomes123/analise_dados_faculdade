"""Processador silver: bronze.recife_acidentes_transito → silver.AcidentesTransito."""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _upsert

logger = logging.getLogger(__name__)

_MERGE_ACID = """\
MERGE silver.AcidentesTransito WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, indicador, periodo, casos, atualizado_em)
ON  tgt.territorio = src.territorio
AND tgt.bairro     = src.bairro
AND tgt.indicador  = src.indicador
AND tgt.periodo    = src.periodo
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, indicador, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.bairro, src.indicador, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_acidentes_transito(connection) -> dict:
    """Transforma acidentes de trânsito do bronze para silver.AcidentesTransito."""
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.recife_acidentes_transito"):
        indicador = p.get("indicador") or ""
        periodo   = p.get("periodo") or ""
        if not indicador or not periodo:
            continue
        params.append((
            p.get("territorio") or "Recife",
            p.get("bairro") or "nao_informado",
            indicador,
            periodo,
            int(p.get("valor") or 0),
            agora,
        ))

    inseridos = _upsert(connection, "silver.AcidentesTransito", _MERGE_ACID, params)
    logger.info("silver.AcidentesTransito: %d linhas processadas", inseridos)
    return {"tabela": "silver.AcidentesTransito", "processados": inseridos}
