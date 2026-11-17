"""Ponto de entrada independente da exportação para a camada Bronze.

Passo 2 da pipeline medallion:
    python3 -m bronze.main

Pré-requisito: mongo.main deve ter sido executado antes para popular o MongoDB.

Responsabilidade:
- Abre conexões com MongoDB e SQL Server.
- Chama pipeline_bronze que copia todas as coleções MongoDB para bronze.
- Fecha as conexões e imprime o resumo.
- Retorna código de saída 0 (sucesso) ou 1 (falha) para o shell/CI.
"""

import logging
import os

from bronze.pipeline import pipeline_bronze
from mongo.config import MONGO_DATABASE
from mongo.database.mongodb import conectar_mongodb


def main() -> int:
    """Lê as coleções MongoDB e persiste os documentos nas tabelas bronze do SQL Server."""
    # LOG_LEVEL da variável de ambiente permite ajustar verbosidade em produção (ex: DEBUG).
    # Padrão INFO mostra progresso sem detalhar cada linha processada.
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # conectar_mongodb: lê MONGODB_URI do .env e cria cliente PyMongo.
    # A conexão é passada para pipeline_bronze que a usa sem fechar.
    cliente = conectar_mongodb()
    try:
        # MONGO_DATABASE = "operacional_db" (definido em mongo/config.py).
        resultados = pipeline_bronze(cliente[MONGO_DATABASE])

        # Soma as estatísticas de todas as coleções exportadas.
        documentos = sum(item["documentos"] for item in resultados)
        inseridos  = sum(item["inseridos"]  for item in resultados)
        print(
            f"Bronze finalizada: {documentos} documentos, "
            f"{inseridos} inseridos nas tabelas SQL Server."
        )
        return 0
    finally:
        # finally garante que a conexão com o MongoDB seja fechada mesmo em exceção.
        cliente.close()


if __name__ == "__main__":
    # raise SystemExit em vez de sys.exit: mais idiomático em Python 3.
    raise SystemExit(main())
