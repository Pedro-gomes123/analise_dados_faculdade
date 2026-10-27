"""Coleta de notificações do SINAN utilizando PySUS."""

from datetime import date

from src.database.mongodb import carregar_documentos
from src.utils.helpers import (
    dataframe_para_registros,
    salvar_json_local,
)


def pipeline_sinan(db):
    print("\n========== PIPELINE PySUS / SINAN ==========")

    try:
        import pysus
    except ImportError as erro:
        print(f"Não foi possível importar o PySUS: {erro}")
        return

    try:
        ano = date.today().year - 1

        print(
            f"Consultando o SINAN para acidentes por "
            f"animais peçonhentos, ano {ano}..."
        )

        # ANIM é o código do agravo de acidentes
        # por animais peçonhentos no SINAN.
        df = pysus.ftp.sinan(
            disease="ANIM",
            year=ano,
            as_dataframe=True,
        )

        if df is None or df.empty:
            print(
                f"Nenhum registro encontrado para o ano {ano}."
            )
            return

        print(f"Registros retornados pelo PySUS: {len(df)}")
        print(f"Colunas disponíveis: {list(df.columns)}")

        # Limita a amostra inicial para validar a integração.
        # O filtro por Pernambuco será implementado após
        # confirmar as colunas de identificação geográfica.
        amostra = df

        registros = dataframe_para_registros(amostra)

        if not registros:
            print("Nenhum registro disponível para salvar.")
            return

        salvar_json_local(
            "pysus_animais_peconhentos",
            registros,
        )

        carregar_documentos(
            db["sinan_animais_peconhentos"],
            "pysus_sinan",
            registros,
            "notificacoes_animais_peconhentos",
            "Brasil - amostra inicial",
        )

        print(
            f"Coleta inicial concluída: "
            f"{len(registros)} registros processados."
        )

    except Exception as erro:
        print(
            f"Falha no pipeline PySUS/SINAN: "
            f"{type(erro).__name__}: {erro}"
        )