"""Executa os coletores de dados e persiste os resultados no MongoDB."""

import logging
import sys

from mongo.config import MONGO_DATABASE
from mongo.database.mongodb import conectar_mongodb
from mongo.collectors.inmet import pipeline_inmet
from mongo.collectors.openmeteo import pipeline_openmeteo
from mongo.collectors.recife import pipeline_recife_arboviroses
from mongo.collectors.s2id import pipeline_s2id
from mongo.collectors.sinan import pipeline_sinan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Executa cada coletor e retorna código diferente de zero se houver falha."""
    logger.info("VigiaClima-Recife — extração para MongoDB")
    try:
        cliente = conectar_mongodb()
    except Exception as erro:
        # Não imprimir a mensagem do driver, que em algumas falhas de URI pode
        # conter detalhes de conexão. O tipo identifica a classe sem segredos.
        logger.error("Não foi possível conectar ao MongoDB (tipo=%s).", type(erro).__name__)
        return 1
    falhas = []
    try:
        db = cliente[MONGO_DATABASE]
        pipelines = [
            ("INMET", pipeline_inmet),
            ("Open-Meteo", pipeline_openmeteo),
            ("Dados Abertos Recife", pipeline_recife_arboviroses),
            ("S2ID / dados.gov.br", pipeline_s2id),
            ("PySUS / SINAN", pipeline_sinan),
        ]

        for nome, funcao in pipelines:
            logger.info("Iniciando fonte: %s", nome)
            try:
                funcao(db)
                logger.info("Fonte concluída: %s", nome)
            except Exception as erro:
                falhas.append(nome)
                logger.error("Falha em %s (tipo=%s).", nome, type(erro).__name__)
    finally:
        cliente.close()
        logger.info("Conexão com MongoDB encerrada.")

    if falhas:
        logger.error("Extração encerrada com fontes em falha: %s", ", ".join(falhas))
        return 1
    logger.info("Todas as fontes finalizaram sem erros.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
