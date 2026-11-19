"""Coleta chamados de acidentes de trânsito via Dados Abertos Recife (CKAN).

Por que acidentes de trânsito?
- Chuva → pista molhada → mais acidentes. É uma das correlações clima-evento
  mais diretas disponíveis com dados abertos.
- O dataset já tem o campo `tempo_clima` que registra a condição climática
  no momento do acidente — cruzamento nativo com dados de precipitação.
- Contém `vitimas` e `vitimasfatais`, que são métricas de impacto real.
- Cobre 2015–2024 com bairro e data, compatível com a granularidade semanal
  do restante do projeto.

Métricas geradas (três indicadores distintos):
  acidente_transito          → número de ocorrências por bairro/semana
  acidente_transito_vitimas  → soma de vítimas feridas
  acidente_transito_fatal    → soma de vítimas fatais
"""

import logging
from collections import defaultdict
from datetime import date
from io import StringIO

import pandas as pd

from mongo.config import CKAN_RECIFE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.http import get
from mongo.utils.storage import dataframe_para_registros, salvar_json_local

logger = logging.getLogger(__name__)

DATASET_ID   = "acidentes-de-transito-com-e-sem-vitimas"
ANOS_RECENTES = 2


def _periodo_semana(data_str) -> str | None:
    """Converte "YYYY-MM-DD" para "YYYY-WNN"."""
    if not data_str or str(data_str).strip().lower() in {"nan", "none", ""}:
        return None
    try:
        dt = date.fromisoformat(str(data_str).strip()[:10])
        iso = dt.isocalendar()
        return f"{iso.year:04d}-W{iso.week:02d}"
    except (ValueError, TypeError):
        return None


def _inteiro(valor) -> int:
    """Converte valor para inteiro, tratando "1,0" (formato brasileiro) e NaN."""
    if valor is None:
        return 0
    s = str(valor).strip().replace(",", ".").split(".")[0]
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def _agregar(registros: list[dict]) -> list[dict]:
    """Agrega acidentes em três métricas por bairro/semana.

    Três indicadores distintos permitem que o app mostre:
    - quantos acidentes ocorreram (ocorrências)
    - quantas pessoas ficaram feridas (vítimas)
    - quantas morreram (vítimas fatais)
    Cada um pode ser cruzado independentemente com precipitação semanal.
    """
    ocorrencias:    dict[tuple, int] = defaultdict(int)
    vitimas:        dict[tuple, int] = defaultdict(int)
    vitimas_fatais: dict[tuple, int] = defaultdict(int)

    for r in registros:
        periodo = _periodo_semana(r.get("data"))
        if not periodo:
            continue
        bairro = str(r.get("bairro") or "nao_informado").strip().upper()
        chave  = (periodo, bairro)

        ocorrencias[chave]    += 1
        vitimas[chave]        += _inteiro(r.get("vitimas"))
        vitimas_fatais[chave] += _inteiro(r.get("vitimasfatais"))

    agregados = []
    for (periodo, bairro), v in sorted(ocorrencias.items()):
        base = {"territorio": "Recife", "bairro": bairro, "periodo": periodo}
        agregados.append({**base, "indicador": "acidente_transito",         "valor": v})
        if vitimas[(periodo, bairro)] > 0:
            agregados.append({**base, "indicador": "acidente_transito_vitimas",
                               "valor": vitimas[(periodo, bairro)]})
        if vitimas_fatais[(periodo, bairro)] > 0:
            agregados.append({**base, "indicador": "acidente_transito_fatal",
                               "valor": vitimas_fatais[(periodo, bairro)]})
    return agregados


def pipeline_acidentes_transito(db):
    """Baixa CSVs de acidentes dos ANOS_RECENTES mais recentes e agrega."""
    logger.info("Iniciando pipeline Acidentes de Trânsito Recife")

    r = get(f"{CKAN_RECIFE}/action/package_show", params={"id": DATASET_ID})
    resultado = r.json()
    if not resultado.get("success"):
        raise RuntimeError(f"CKAN Recife não retornou dataset {DATASET_ID!r}.")

    recursos = resultado["result"].get("resources", [])
    csvs = sorted(
        [rc for rc in recursos if rc.get("format","").upper() == "CSV" and rc.get("url")],
        key=lambda rc: rc.get("name", ""),
        reverse=True,       # mais recentes primeiro (nome inclui o ano)
    )[:ANOS_RECENTES]

    if not csvs:
        raise RuntimeError("Acidentes: nenhum recurso CSV encontrado.")

    todos: list[dict] = []
    for recurso in csvs:
        try:
            resp = get(recurso["url"])
            try:
                texto = resp.content.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = resp.content.decode("latin-1")
            df = pd.read_csv(StringIO(texto), sep=None, engine="python")
            linhas = dataframe_para_registros(df)
            todos.extend(linhas)
            logger.info("Acidentes %s: %d linhas", recurso.get("name"), len(linhas))
        except Exception as e:
            logger.error("Falha ao baixar acidentes %s: %s", recurso.get("name"), type(e).__name__)

    if not todos:
        raise RuntimeError("Acidentes: nenhuma linha carregada.")

    agregados = _agregar(todos)
    if not agregados:
        raise RuntimeError("Acidentes: nenhum registro com data válida.")

    salvar_json_local("acidentes_transito_recife", agregados)

    carregar_documentos(
        db["recife_acidentes_transito"],
        "dados_abertos_recife",
        agregados,
        "acidentes_transito_semanais",
        "Recife",
        campos_chave=("indicador", "periodo", "bairro"),
    )
    logger.info("Acidentes concluído: %d grupos agregados", len(agregados))
