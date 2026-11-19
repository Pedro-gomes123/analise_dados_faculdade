"""Orquestrador da pipeline silver: coordena todos os processadores.

Cada processador vive em seu próprio módulo dentro de silver/pipelines/.
Este arquivo apenas importa, lista e executa em sequência, isolando falhas.
"""

import logging

from silver.pipelines._base import _aplicar_ddl
from silver.pipelines.meteorologia import processar_meteorologia
from silver.pipelines.arboviroses import processar_arboviroses
from silver.pipelines.defesa_civil import processar_defesa_civil
from silver.pipelines.animais_peconhentos import processar_animais_peconhentos
from silver.pipelines.samu import processar_samu
from silver.pipelines.acidentes_transito import processar_acidentes_transito
from silver.pipelines.estacoes import processar_estacoes

logger = logging.getLogger(__name__)


def silver_pipeline(connection=None, aplicar_ddl: bool = True) -> list[dict]:
    """Executa todos os processadores bronze → silver em sequência.

    Falha em um processador não interrompe os demais — cada um roda
    independentemente e registra seu próprio erro em log.

    Args:
        connection: Conexão pyodbc pré-existente; se None, abre automaticamente.
        aplicar_ddl: Se True, executa o DDL silver antes de processar.

    Returns:
        Lista de dicts com "tabela", "processados" e opcionalmente "erro".
    """
    from silver.database.sql_server import conectar_sql_server

    owns = connection is None
    if owns:
        connection = conectar_sql_server()

    try:
        if aplicar_ddl:
            _aplicar_ddl(connection)

        fontes = [
            processar_meteorologia,
            processar_arboviroses,
            processar_defesa_civil,
            processar_animais_peconhentos,
            processar_samu,
            processar_acidentes_transito,
            processar_estacoes,
        ]
        resultados = []
        for fn in fontes:
            try:
                resultados.append(fn(connection))
            except Exception as erro:
                logger.error("Falha em %s: %s", getattr(fn, "__name__", repr(fn)), type(erro).__name__)
                resultados.append({
                    "tabela":      getattr(fn, "__name__", repr(fn)),
                    "processados": 0,
                    "erro":        str(erro),
                })

        total = sum(r.get("processados", 0) for r in resultados)
        logger.info("Pipeline Silver concluído: %d linhas no total", total)
        return resultados
    finally:
        if owns:
            connection.close()
