"""Ponto de entrada independente da exportação para a camada Bronze.

Passo 2 da pipeline medallion:
    python3 -m bronze.main

Pré-requisito: mongo.main deve ter sido executado antes para popular o MongoDB.
"""

import logging
import os

from bronze.pipeline import pipeline_bronze
from mongo.config import MONGO_DATABASE
from mongo.database.mongodb import conectar_mongodb


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        cliente = conectar_mongodb()
    except Exception as erro:
        logger.error("Não foi possível conectar ao MongoDB (tipo=%s).", type(erro).__name__)
        return 1

    try:
        resultados = pipeline_bronze(cliente[MONGO_DATABASE])
        documentos = sum(item["documentos"] for item in resultados)
        inseridos  = sum(item["inseridos"]  for item in resultados)
        print(
            f"Bronze finalizada: {documentos} documentos, "
            f"{inseridos} inseridos nas tabelas SQL Server."
        )
        return 0
    except Exception as erro:
        logger.error("Pipeline Bronze falhou (tipo=%s).", type(erro).__name__)
        return 1
    finally:
        cliente.close()


if __name__ == "__main__":
    raise SystemExit(main())
