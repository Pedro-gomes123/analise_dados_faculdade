"""Conexão e persistência no MongoDB Atlas."""

import hashlib
import json
import os
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne

from src.config import MONGO_DATABASE
from src.utils.helpers import normalizar_registro


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

    cliente.admin.command("ping")

    print("Conexão com MongoDB Atlas estabelecida.")

    return cliente


def carregar_documentos(
    collection,
    fonte,
    registros,
    tipo_dado,
    municipio="Recife",
):
    """
    Grava documentos com identificadores determinísticos.

    O uso de $setOnInsert impede a substituição de documentos
    existentes com o mesmo identificador.
    """

    agora = datetime.now(timezone.utc)
    operacoes = []

    for registro in registros:
        payload = normalizar_registro(registro)

        assinatura = json.dumps(
            payload,
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

        operacoes.append(
            UpdateOne(
                {"_id": identificador},
                {"$setOnInsert": documento},
                upsert=True,
            )
        )

    if not operacoes:
        print(
            f"Nenhum registro para inserir em {collection.name}."
        )

        return {
            "recebidos": 0,
            "novos": 0,
        }

    resultado = collection.bulk_write(
        operacoes,
        ordered=False,
    )

    novos = resultado.upserted_count

    print(
        f"{collection.name}: "
        f"{len(operacoes)} registros recebidos; "
        f"{novos} novos; "
        f"{len(operacoes) - novos} já existiam."
    )

    return {
        "recebidos": len(operacoes),
        "novos": novos,
    }