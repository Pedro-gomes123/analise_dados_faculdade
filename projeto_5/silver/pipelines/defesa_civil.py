"""Processador silver: bronze.recife_defesa_civil → silver.DefesaCivil."""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _upsert

logger = logging.getLogger(__name__)

_MERGE_DC = """\
MERGE silver.DefesaCivil WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, tipo_ocorrencia, periodo, casos, atualizado_em)
ON  tgt.territorio      = src.territorio
AND tgt.tipo_ocorrencia = src.tipo_ocorrencia
AND tgt.periodo         = src.periodo
AND tgt.bairro          = src.bairro
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, tipo_ocorrencia, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.bairro, src.tipo_ocorrencia, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_defesa_civil(connection) -> dict:
    """Transforma atendimentos da Defesa Civil do bronze para silver.DefesaCivil."""
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.recife_defesa_civil"):
        tipo    = p.get("tipo_ocorrencia") or ""
        periodo = p.get("periodo") or ""
        if not tipo or not periodo:
            continue
        params.append((
            p.get("territorio") or "Recife",
            p.get("bairro") or "nao_informado",
            tipo,
            periodo,
            int(p.get("valor") or 0),
            agora,
        ))

    inseridos = _upsert(connection, "silver.DefesaCivil", _MERGE_DC, params)
    logger.info("silver.DefesaCivil: %d linhas processadas", inseridos)
    return {"tabela": "silver.DefesaCivil", "processados": inseridos}
