"""CLI da carga piloto Bronze → Staging → Silver para INMET estações."""

import logging
import os
import sys

from silver.pipelines.silver_pipeline import silver_pipeline


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    try:
        result = silver_pipeline()
    except Exception as error:
        logger = logging.getLogger(__name__)
        if isinstance(error, RuntimeError):
            # RuntimeErrors deste projeto contêm mensagens higienizadas, sem
            # connection strings nem valores de credenciais.
            logger.error("Execução Silver encerrada com falha: %s", error)
        else:
            logger.error(
                "Execução Silver encerrada com falha (tipo=%s).",
                type(error).__name__,
            )
        return 1
    print(
        "Piloto INMET finalizado: "
        f"staging={result['registros_inseridos_staging']}, "
        f"silver={result['registros_inseridos']}, "
        f"rejeitados={result['registros_rejeitados']}, "
        f"status={result['status']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
