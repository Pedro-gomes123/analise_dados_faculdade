"""Processador silver: bronze.recife_samu → silver.SAMU."""

import logging
from datetime import datetime, timezone

from silver.pipelines._base import _ler_bronze, _upsert

logger = logging.getLogger(__name__)

_MERGE_SAMU = """\
MERGE silver.SAMU WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, ?, CONVERT(datetimeoffset(6), ?))) AS src
    (territorio, bairro, tipo_emergencia, periodo, casos, atualizado_em)
ON  tgt.territorio      = src.territorio
AND tgt.bairro          = src.bairro
AND tgt.tipo_emergencia = src.tipo_emergencia
AND tgt.periodo         = src.periodo
WHEN NOT MATCHED THEN
    INSERT (territorio, bairro, tipo_emergencia, periodo, casos, atualizado_em)
    VALUES (src.territorio, src.bairro, src.tipo_emergencia, src.periodo, src.casos, src.atualizado_em)
WHEN MATCHED THEN UPDATE SET casos = src.casos, atualizado_em = src.atualizado_em;
"""


def processar_samu(connection) -> dict:
    """Transforma chamados SAMU do bronze para silver.SAMU."""
    agora = datetime.now(timezone.utc).isoformat()
    params = []
    for p in _ler_bronze(connection, "bronze.recife_samu"):
        # indicador no MongoDB: "samu_<tipo>" — extrai o tipo após o prefixo.
        indicador = p.get("indicador") or ""
        tipo = indicador.removeprefix("samu_") if indicador.startswith("samu_") else indicador
        periodo   = p.get("periodo") or ""
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

    inseridos = _upsert(connection, "silver.SAMU", _MERGE_SAMU, params)
    logger.info("silver.SAMU: %d linhas processadas", inseridos)
    return {"tabela": "silver.SAMU", "processados": inseridos}
