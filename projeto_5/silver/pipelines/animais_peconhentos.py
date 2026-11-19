"""Processador silver: bronze.sinan_animais_peconhentos → silver.AnimaisPerconhentos."""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _upsert

logger = logging.getLogger(__name__)

_MERGE_ANI = """\
MERGE silver.AnimaisPerconhentos WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, municipio, codigo_municipio, periodo, casos, atualizado_em)
ON  tgt.territorio       = src.territorio
AND tgt.municipio        = src.municipio
AND tgt.codigo_municipio = src.codigo_municipio
AND tgt.periodo          = src.periodo
WHEN NOT MATCHED THEN
    INSERT (territorio, municipio, codigo_municipio, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.municipio, src.codigo_municipio, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_animais_peconhentos(connection) -> dict:
    """Transforma acidentes SINAN do bronze para silver.AnimaisPerconhentos."""
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.sinan_animais_peconhentos"):
        periodo = p.get("periodo") or ""
        if not periodo:
            continue
        params.append((
            p.get("territorio") or "Pernambuco",
            p.get("municipio") or "nao_informado",
            p.get("codigo_municipio") or "nao_informado",
            periodo,
            int(p.get("valor") or 0),
            agora,
        ))

    inseridos = _upsert(connection, "silver.AnimaisPerconhentos", _MERGE_ANI, params)
    logger.info("silver.AnimaisPerconhentos: %d linhas processadas", inseridos)
    return {"tabela": "silver.AnimaisPerconhentos", "processados": inseridos}
