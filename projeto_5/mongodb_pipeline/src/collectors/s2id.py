"""Coleta de dados de desastres via dados.gov.br."""

from io import BytesIO, StringIO

import pandas as pd

from src.config import CKAN_GOV
from src.database.mongodb import carregar_documentos
from src.utils.helpers import (
    dataframe_para_registros,
    get,
    normalizar_registro,
    salvar_json_local,
)


def pipeline_s2id(db):
    print("\n========== PIPELINE S2ID / DADOS.GOV.BR ==========")

    termos = [
        "s2id desastre",
        "calamidade publica",
        "defesa civil emergencia",
    ]

    encontrados = {}

    for termo in termos:
        try:
            resposta = get(
                f"{CKAN_GOV}/action/package_search",
                params={
                    "q": termo,
                    "rows": 5,
                },
            )

            resultado = resposta.json()

            if resultado.get("success"):
                datasets = resultado.get(
                    "result", {}
                ).get("results", [])

                for dataset in datasets:
                    encontrados[dataset.get("id")] = dataset

        except Exception as erro:
            print(
                f"Busca '{termo}' falhou: "
                f"{type(erro).__name__}: {erro}"
            )

    registros_finais = []

    for dataset in encontrados.values():
        for recurso in dataset.get("resources", []):
            formato = str(
                recurso.get("format") or ""
            ).upper()

            if formato not in {"CSV", "JSON", "XLSX"}:
                continue

            if not recurso.get("url"):
                continue

            try:
                print(
                    f"Recurso: {dataset.get('title')} / "
                    f"{recurso.get('name')} ({formato})"
                )

                resp = get(recurso["url"])
                df = None

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

                elif formato == "JSON":
                    conteudo = resp.json()

                    if isinstance(conteudo, list):
                        registros = [
                            normalizar_registro(item)
                            for item in conteudo[:200]
                        ]
                    elif isinstance(conteudo, dict):
                        registros = [
                            normalizar_registro(conteudo)
                        ]
                    else:
                        registros = []

                else:
                    df = pd.read_excel(
                        BytesIO(resp.content)
                    )

                if df is not None:
                    registros = dataframe_para_registros(
                        df.head(200)
                    )

                for registro in registros:
                    registro["_dataset_id"] = dataset.get("id")
                    registro["_dataset_titulo"] = dataset.get("title")
                    registro["_recurso_nome"] = recurso.get("name")

                if registros:
                    chaves = {
                        str(chave).lower(): chave
                        for chave in registros[0].keys()
                    }

                    coluna_uf = next(
                        (
                            chaves[chave]
                            for chave in ("uf", "estado", "sg_uf")
                            if chave in chaves
                        ),
                        None,
                    )

                    if coluna_uf:
                        registros_pe = [
                            registro
                            for registro in registros
                            if str(
                                registro.get(coluna_uf, "")
                            ).upper()
                            in {"PE", "PERNAMBUCO"}
                        ]

                        if registros_pe:
                            registros = registros_pe

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
            "Não foi possível baixar um recurso de desastres."
        )
        return

    salvar_json_local(
        "s2id_desastres",
        registros_finais,
    )

    carregar_documentos(
        db["s2id_desastres"],
        "dados_gov_s2id",
        registros_finais,
        "desastres",
    )