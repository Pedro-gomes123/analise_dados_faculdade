"""Ponto de entrada da camada Gold.

Passo 4 (final) da pipeline medallion:
    python3 -m gold.main

Pré-requisito: silver.main deve ter sido executado com sucesso antes deste módulo.

Executa dois pipelines independentes:
1. gold_pipeline   — silver → gold (leitura_climatica + indicador_territorio)
2. dim_pipeline    — popula dimensões estáticas (tempo, territorio, indicador, fonte)
"""

import logging
import os

from gold.pipelines.gold_pipeline import gold_pipeline
from gold.pipelines.dim_pipeline import dim_pipeline


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    codigo = 0

    # --- Gold Pipeline (silver → gold) --------------------------------------
    try:
        print("--- Gold Pipeline ---")
        resultados = gold_pipeline()
        for r in resultados:
            erro   = r.get("erro")
            status = f"ERRO: {erro}" if erro else f"{r['processados']} linhas"
            print(f"  {r['tabela']}: {status}")
            if erro:
                codigo = 1
        total = sum(r.get("processados", 0) for r in resultados)
        print(f"Gold finalizada: {total} linhas processadas.")
    except Exception as erro:
        logger.error("Pipeline Gold falhou (tipo=%s).", type(erro).__name__)
        codigo = 1

    # --- Dim Pipeline (tabelas de dimensão) ----------------------------------
    try:
        print("--- Dim Pipeline ---")
        dim_pipeline()
        print("Dimensões atualizadas.")
    except Exception as erro:
        logger.error("Pipeline Dim falhou (tipo=%s).", type(erro).__name__)
        codigo = 1

    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
