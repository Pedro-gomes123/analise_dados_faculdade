"""Ponto de entrada da pipeline VigiaClima-Recife."""

import sys

from src.config import MONGO_DATABASE
from src.database.mongodb import conectar_mongodb

from src.collectors.inmet import pipeline_inmet
from src.collectors.openmeteo import pipeline_openmeteo
from src.collectors.recife import pipeline_recife_arboviroses
from src.collectors.s2id import pipeline_s2id
from src.collectors.sinan import pipeline_sinan


def main():
    print("=" * 65)
    print("VigiaClima-Recife — Pipeline de ingestão")
    print("=" * 65)

    cliente = conectar_mongodb()
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
            print(f"\nIniciando: {nome}")

            try:
                funcao(db)
                print(f"Finalizado: {nome}")

            except Exception as erro:
                falhas.append(nome)

                print(
                    f"Falha em {nome}: "
                    f"{type(erro).__name__}: {erro}"
                )

        print("\n" + "=" * 65)
        print("Execução da pipeline finalizada.")

        if falhas:
            print("Fontes com falha:", ", ".join(falhas))
            sys.exit(1)

        print("Todas as fontes finalizaram sem erros.")

    finally:
        cliente.close()
        print("Conexão com MongoDB encerrada.")


if __name__ == "__main__":
    main()