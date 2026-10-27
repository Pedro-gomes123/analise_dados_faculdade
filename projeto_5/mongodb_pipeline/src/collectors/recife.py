"""Coleta de dados de arboviroses do portal do Recife."""

from io import StringIO

import pandas as pd

from src.config import CKAN_RECIFE
from src.database.mongodb import carregar_documentos
from src.utils.helpers import (
    dataframe_para_registros,
    get,
    normalizar_registro,
    salvar_json_local,
)


def pipeline_recife_arboviroses(db):
    print("\n========== PIPELINE DADOS ABERTOS RECIFE ==========")

    resposta = get(
        f"{CKAN_RECIFE}/action/package_search",
        params={
            "q": "dengue zika chikungunya",
            "rows": 10,
        },
    )

    resultado = resposta.json()

    if not resultado.get("success"):
        raise RuntimeError(
            "O portal CKAN Recife não confirmou a busca."
        )

    datasets = resultado.get("result", {}).get("results", [])
    registros_finais = []

    for dataset in datasets:
        for recurso in dataset.get("resources", []):
            formato = str(
                recurso.get("format") or ""
            ).upper()

            if formato not in {"CSV", "JSON"}:
                continue

            if not recurso.get("url"):
                continue

            try:
                print(
                    f"Recurso: {dataset.get('title')} / "
                    f"{recurso.get('name')} ({formato})"
                )

                resp = get(recurso["url"])

                if formato == "CSV":
                    try:
                        conteudo = resp.content.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        conteudo = resp.content.decode("latin-1")

                    df = pd.read_csv(
                        StringIO(conteudo),
                        sep=None,
                        engine="python",
                    )

                    registros = dataframe_para_registros(
                        df.head(100)
                    )

                else:
                    conteudo = resp.json()

                    if isinstance(conteudo, list):
                        registros = [
                            normalizar_registro(item)
                            for item in conteudo[:100]
                        ]
                    elif isinstance(conteudo, dict):
                        registros = [
                            normalizar_registro(conteudo)
                        ]
                    else:
                        registros = []

                for registro in registros:
                    registro["_dataset_id"] = dataset.get("id")
                    registro["_dataset_titulo"] = dataset.get("title")
                    registro["_recurso_nome"] = recurso.get("name")

                if registros:
                    registros_finais = registros
                    break

            except Exception as erro:
                print(
                    f"Recurso não pôde ser carregado: "
                    f"{type(erro).__name__}: {erro}"
                )

        if registros_finais:
            break

    if not registros_finais:
        print(
            "Nenhum recurso CSV/JSON disponível foi baixado."
        )
        return

    salvar_json_local(
        "dados_abertos_recife_arboviroses",
        registros_finais,
    )

    carregar_documentos(
        db["recife_arboviroses"],
        "dados_abertos_recife",
        registros_finais,
        "arboviroses",
    )