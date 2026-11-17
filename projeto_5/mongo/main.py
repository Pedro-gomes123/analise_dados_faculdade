"""Orquestrador da camada de coleta MongoDB (passo 1 da pipeline medallion).

Executa todos os coletores em sequência e persiste os resultados no MongoDB Atlas.
Ordem de execução (1 de 4 camadas da arquitetura medallion):

    python3 -m mongo.main     # 1. APIs externas → MongoDB (este arquivo)
    python3 -m bronze.main    # 2. MongoDB → bronze SQL Server
    python3 -m silver.main    # 3. bronze → silver SQL Server
    python3 -m gold.main      # 4. silver → gold SQL Server

Por que MongoDB como camada de staging?
- As APIs externas retornam formatos heterogêneos (JSON, CSV, DBC binário).
  O MongoDB aceita qualquer estrutura de documento sem schema pré-definido.
- Permite re-executar o bronze sem precisar chamar as APIs novamente
  (desacopla coleta de transformação).
- O SHA-256 _id garante idempotência: re-execuções não duplicam dados.
"""

import logging
import sys

from mongo.config import MONGO_DATABASE
from mongo.database.mongodb import conectar_mongodb
from mongo.collectors.openmeteo import pipeline_openmeteo
from mongo.collectors.openmeteo_historico import pipeline_openmeteo_historico
from mongo.collectors.nasa_power import pipeline_nasa_power
from mongo.collectors.recife import pipeline_recife_arboviroses
from mongo.collectors.defesa_civil import pipeline_defesa_civil
from mongo.collectors.sinan import pipeline_sinan

# basicConfig define o formato global de log para toda a execução.
# %(asctime)s: timestamp ISO  |  %(levelname)s: INFO/WARNING/ERROR
# %(name)s: nome do módulo (ex: "mongo.collectors.openmeteo")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Executa cada coletor em sequência e retorna código de saída.

    Por que falha isolada por coletor (e não abortar tudo)?
    - Cada API é independente. Uma falha na CKAN Recife não impede coletar
      dados climáticos da NASA POWER.
    - O projeto monitora `falhas` e retorna código 1 se qualquer coletor
      falhar, mas sem interromper os demais — garante dados parciais em vez
      de execução totalmente vazia.

    Returns:
        0 se todas as fontes terminaram sem erro, 1 se ao menos uma falhou.
    """
    logger.info("VigiaClima-Recife — extração para MongoDB")

    # Conecta ao MongoDB Atlas; falha aqui aborta tudo (não há como prosseguir
    # sem banco). Não imprime a mensagem de erro do driver para evitar vazar
    # detalhes da URI (que contém usuário e senha).
    try:
        cliente = conectar_mongodb()
    except Exception as erro:
        logger.error("Não foi possível conectar ao MongoDB (tipo=%s).", type(erro).__name__)
        return 1

    falhas = []
    try:
        db = cliente[MONGO_DATABASE]  # seleciona o database "operacional_db"

        # Lista de pares (nome legível, função de pipeline).
        # O nome é usado apenas em logs — não afeta a execução.
        pipelines = [
            ("Open-Meteo Forecast",   pipeline_openmeteo),
            ("Open-Meteo Archive ERA5", pipeline_openmeteo_historico),
            ("NASA POWER",            pipeline_nasa_power),
            ("Dados Abertos Recife",  pipeline_recife_arboviroses),
            ("Defesa Civil Recife",   pipeline_defesa_civil),
            ("PySUS / SINAN",         pipeline_sinan),
        ]

        for nome, funcao in pipelines:
            logger.info("Iniciando fonte: %s", nome)
            try:
                # Cada pipeline recebe `db` (pymongo Database) e persiste
                # seus documentos diretamente na coleção correspondente.
                funcao(db)
                logger.info("Fonte concluída: %s", nome)
            except Exception as erro:
                # Registra a falha sem re-lançar — os demais coletores continuam.
                # type(erro).__name__ expõe o tipo sem mensagem (pode conter URIs).
                falhas.append(nome)
                logger.error("Falha em %s (tipo=%s).", nome, type(erro).__name__)
    finally:
        # Garante que a conexão seja fechada mesmo em caso de exceção inesperada.
        cliente.close()
        logger.info("Conexão com MongoDB encerrada.")

    if falhas:
        logger.error("Extração encerrada com fontes em falha: %s", ", ".join(falhas))
        return 1  # sinaliza ao orquestrador (CI/cron) que houve problema

    logger.info("Todas as fontes finalizaram sem erros.")
    return 0


if __name__ == "__main__":
    # sys.exit() com o retorno de main() propaga o código de saída para o shell,
    # permitindo que scripts de CI (GitHub Actions, Airflow) detectem falhas.
    sys.exit(main())
