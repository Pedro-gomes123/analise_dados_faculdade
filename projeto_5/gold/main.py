"""Ponto de entrada da camada Gold.

Passo 4 (final) da pipeline medallion:
    python3 -m gold.main

Pré-requisito: silver.main deve ter sido executado com sucesso antes deste módulo.

Executa dois pipelines em sequência:

1. gold_pipeline — transforma silver → gold:
   - gold.leitura_climatica: formato longo (UNPIVOT) com uma variável por linha.
   - gold.estacao: catálogo de estações INMET para o app.
   - gold.indicador_territorio: unifica saúde e desastres por bairro/período.

2. dim_pipeline — popula tabelas de dimensão (dados de referência):
   - dim.Tempo: calendário 2018–2030 com semana ISO, estação do ano, etc.
   - dim.Territorio: hierarquia geográfica de Recife (RPAs → bairros).
   - dim.Indicador: catálogo de indicadores com limiares de alerta/crítico.
   - dim.Fonte: metadados operacionais de cada API (URL, frequência, licença).

Por que dimensões separadas do gold_pipeline?
As dimensões são dados de referência estáticos (ou quase). Separá-las em um
pipeline dedicado permite atualizá-las sem reprocessar os dados factuais e
vice-versa.
"""

import logging
import os

from gold.pipelines.gold_pipeline import gold_pipeline
from gold.pipelines.dim_pipeline import dim_pipeline


def main() -> int:
    """Executa gold_pipeline e dim_pipeline em sequência; retorna código de saída."""
    # LOG_LEVEL da variável de ambiente: INFO por padrão, DEBUG em desenvolvimento.
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # codigo acumula falhas: 0 = tudo OK, 1 = ao menos um pipeline falhou.
    # Os dois pipelines rodam independentemente — falha no gold não cancela o dim.
    codigo = 0

    # --- Gold Pipeline (silver → gold) --------------------------------------
    try:
        print("--- Gold Pipeline ---")
        resultados = gold_pipeline()

        # Exibe resultado por tabela gold: linhas processadas ou mensagem de erro.
        for r in resultados:
            erro   = r.get("erro")
            status = f"ERRO: {erro}" if erro else f"{r['processados']} linhas"
            print(f"  {r['tabela']}: {status}")

        total = sum(r.get("processados", 0) for r in resultados)
        print(f"Gold finalizada: {total} linhas processadas.")
    except Exception as erro:
        # Exceção não tratada no gold_pipeline — falha geral, não por processador.
        logging.error("Pipeline Gold falhou: %s", erro)
        codigo = 1

    # --- Dim Pipeline (tabelas de dimensão) ----------------------------------
    try:
        print("--- Dim Pipeline ---")
        # dim_pipeline aplica DDL idempotente e popula via INSERT WHERE NOT EXISTS.
        dim_pipeline()
        print("Dimensões atualizadas.")
    except Exception as erro:
        logging.error("Pipeline Dim falhou: %s", erro)
        codigo = 1

    # Retorna 0 se ambos os pipelines tiveram sucesso, 1 caso contrário.
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
