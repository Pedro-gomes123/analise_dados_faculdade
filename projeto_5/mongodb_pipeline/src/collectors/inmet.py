
"""Coleta de dados do INMET."""

from datetime import date, timedelta

from src.config import INMET_BASE, ESTACAO_RECIFE
from src.database.mongodb import carregar_documentos
from src.utils.helpers import get, salvar_json_local


def pipeline_inmet(db):
    print("\n========== PIPELINE INMET ==========")

    # 1. Consulta as estações automáticas.
    resposta = get(f"{INMET_BASE}/estacoes/T")
    estacoes = resposta.json()

    salvar_json_local("inmet_estacoes", estacoes)

    estacoes_pe = [
        estacao
        for estacao in estacoes
        if str(estacao.get("SG_ESTADO", "")).upper() == "PE"
    ]

    carregar_documentos(
        db["inmet_estacoes"],
        "inmet",
        estacoes_pe,
        "estacao_automatica",
        "Pernambuco",
    )

    # 2. Consulta observações recentes da estação A301.
    fim = date.today()
    inicio = fim - timedelta(days=2)

    url = (
        f"{INMET_BASE}/estacao/"
        f"{inicio.isoformat()}/"
        f"{fim.isoformat()}/"
        f"{ESTACAO_RECIFE}"
    )

    resposta_dados = get(url)

    # HTTP 204 significa que a resposta não possui conteúdo.
    if resposta_dados.status_code == 204 or not resposta_dados.content:
        print(
            f"INMET: nenhuma observação disponível para a estação "
            f"{ESTACAO_RECIFE} entre {inicio} e {fim}."
        )
        return

    # 3. Converte a resposta para JSON.
    dados = resposta_dados.json()

    salvar_json_local(f"inmet_{ESTACAO_RECIFE}", dados)

    if isinstance(dados, list):
        registros = dados
    elif isinstance(dados, dict):
        registros = [dados]
    else:
        registros = []

    # 4. Persiste as observações no MongoDB.
    carregar_documentos(
        db["inmet_observacoes"],
        "inmet",
        registros,
        "observacao_horaria",
        "Recife",
    )

    print("Finalizado: INMET")
