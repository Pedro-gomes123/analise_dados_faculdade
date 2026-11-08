"""Conexão e persistência no MongoDB Atlas."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne

from mongo.utils.helpers import normalizar_registro

logger = logging.getLogger(__name__)


def conectar_mongodb():
    """Conecta ao Atlas usando a variável de ambiente MONGODB_URI."""

    uri = os.environ.get("MONGODB_URI")

    if not uri:
        raise RuntimeError(
            "A variável de ambiente MONGODB_URI não foi configurada."
        )

    cliente = MongoClient(
        uri,
        serverSelectionTimeoutMS=15000,
    )

    try:
        cliente.admin.command("ping")
    except Exception:
        cliente.close()
        raise

    logger.info("Conexão com MongoDB Atlas estabelecida.")

    return cliente


def carregar_documentos(
    collection,
    fonte,
    registros,
    tipo_dado,
    municipio="Recife",
    campos_chave=None,
):

    agora = datetime.now(timezone.utc)
    registros = list(registros)
    por_id = {}

    for registro in registros:
        payload = normalizar_registro(registro)

        chave = (
            {campo: payload.get(campo) for campo in campos_chave}
            if campos_chave
            else payload
        )
        if campos_chave and any(valor is None for valor in chave.values()):
            raise ValueError(
                f"Registro sem campo necessário para chave idempotente: {campos_chave}"
            )
        assinatura = json.dumps(
            chave,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        identificador = hashlib.sha256(
            f"{fonte}|{tipo_dado}|{assinatura}".encode("utf-8")
        ).hexdigest()

        documento = {
            "_id": identificador,
            "fonte": fonte,
            "tipo_dado": tipo_dado,
            "municipio": municipio,
            "ingestao_ts": agora,
            "payload": payload,
        }

        por_id[identificador] = documento

    operacoes = [
        UpdateOne(
            {"_id": identificador},
            {
                "$set": {chave: valor for chave, valor in documento.items() if chave != "_id"},
                "$setOnInsert": {"_id": identificador},
            },
            upsert=True,
        )
        for identificador, documento in por_id.items()
    ]

    if not operacoes:
        logger.info("Nenhum registro para inserir em %s.", collection.name)

        return {
            "recebidos": 0,
            "novos": 0,
        }

    resultado = collection.bulk_write(
        operacoes,
        ordered=False,
    )

    novos = resultado.upserted_count

    logger.info(
        "%s: %d registros recebidos, %d IDs únicos, %d novos, %d atualizados.",
        collection.name,
        len(registros),
        len(operacoes),
        novos,
        resultado.modified_count,
    )

    return {
        "recebidos": len(registros),
        "novos": novos,
        "ids_unicos": len(operacoes),
    }
