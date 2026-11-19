"""Ponto de entrada da camada Silver.

Passo 3 da pipeline medallion:
    python3 -m silver.main

Pré-requisito: bronze.main deve ter sido executado antes.
"""

import logging
import os

from silver.pipelines.silver_pipeline import silver_pipeline


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        resultados = silver_pipeline()
    except Exception as erro:
        logger.error("Pipeline Silver falhou (tipo=%s).", type(erro).__name__)
        return 1

    houve_erro = False
    for r in resultados:
        erro   = r.get("erro")
        status = f"ERRO: {erro}" if erro else f"{r['processados']} linhas"
        print(f"  {r['tabela']}: {status}")
        if erro:
            houve_erro = True

    total = sum(r.get("processados", 0) for r in resultados)
    print(f"Silver finalizada: {total} linhas processadas.")
    return 1 if houve_erro else 0


if __name__ == "__main__":
    raise SystemExit(main())
