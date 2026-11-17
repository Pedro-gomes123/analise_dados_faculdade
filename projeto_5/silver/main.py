"""Ponto de entrada da camada Silver.

Passo 3 da pipeline medallion:
    python3 -m silver.main

Pré-requisito: bronze.main deve ter sido executado antes para popular as tabelas bronze.

Responsabilidade:
- Chama silver_pipeline que lê bronze, transforma e persiste nas tabelas silver.
- Imprime resumo por tabela: linhas processadas ou mensagem de erro.
- Retorna código de saída 0 (sucesso) ou 1 (falha) para o shell/CI.

Transformações realizadas pela silver:
- Desserializa payload_json (BSON Extended JSON → Python).
- Normaliza timestamps para DATETIMEOFFSET UTC.
- Converte pressão de kPa (NASA POWER) para hPa (padrão do projeto).
- Agrega contagens de saúde/desastres por período e território.
- Aplica MERGE idempotente: re-executar não duplica dados.
"""

import logging
import os

from silver.pipelines.silver_pipeline import silver_pipeline


def main() -> int:
    """Orquestra a transformação bronze → silver e imprime o resumo."""
    # LOG_LEVEL da variável de ambiente — permite DEBUG em desenvolvimento
    # sem alterar o código.
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        resultados = silver_pipeline()

        # Exibe resultado por tabela: linhas processadas ou erro isolado.
        # Uma falha em uma tabela não impede as demais (isolamento do silver_pipeline).
        for r in resultados:
            erro   = r.get("erro")
            status = f"ERRO: {erro}" if erro else f"{r['processados']} linhas"
            print(f"  {r['tabela']}: {status}")

        total = sum(r.get("processados", 0) for r in resultados)
        print(f"Silver finalizada: {total} linhas processadas.")
        return 0
    except Exception as erro:
        # Captura exceções não tratadas no silver_pipeline (ex: falha de conexão SQL).
        logging.error("Pipeline Silver falhou: %s", erro)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
