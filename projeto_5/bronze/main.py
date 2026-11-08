"""Ponto de entrada independente da exportação para a camada Bronze."""

import logging
import os

from bronze.pipeline import pipeline_bronze
from mongo.config import MONGO_DATABASE
from mongo.database.mongodb import conectar_mongodb


def main() -> int:
    """Lê as coleções MongoDB e publica os snapshots Parquet no Azure."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cliente = conectar_mongodb()
    try:
        resultados = pipeline_bronze(cliente[MONGO_DATABASE])
        documentos = sum(item["documentos"] for item in resultados)
        arquivos = sum(item["blob"] is not None for item in resultados)
        print(
            f"Bronze finalizada: {documentos} documentos em "
            f"{arquivos} arquivos Parquet."
        )
        return 0
    finally:
        cliente.close()


if __name__ == "__main__":
    raise SystemExit(main())
