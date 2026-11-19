"""Coleta chamados do SAMU Recife via Dados Abertos Recife (CKAN).

Por que o SAMU é relevante para o projeto?
- Chamados de emergência são um proxy direto de impacto climático na saúde:
  ondas de calor → aumento de chamados cardiológicos e clínicos;
  chuvas intensas → aumento de traumas por acidentes e afogamentos.
- Os dados têm bairro e data, permitindo correlação semanal com
  precipitação, temperatura e umidade do gold.leitura_climatica.
- O dataset cobre de 2011 a 2026 — série histórica longa para análise.

Estratégia de coleta:
Tenta baixar os ANOS_RECENTES anos mais recentes a partir do ano atual.
O ID do dataset segue o padrão "samu-{ano}", então iteramos anos decrescentes.
"""

import logging
import re
from collections import defaultdict
from datetime import date
from io import StringIO

import pandas as pd

from mongo.config import CKAN_RECIFE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.http import get
from mongo.utils.storage import dataframe_para_registros, salvar_json_local

logger = logging.getLogger(__name__)

ANOS_RECENTES = 2
_DATASET_PREFIXO = "servico-de-atendimento-movel-de-urgencia-samu"


def _periodo_semana(data_str: str) -> str | None:
    """Converte data ISO "YYYY-MM-DD" para semana ISO "YYYY-WNN"."""
    if not data_str or str(data_str).strip().lower() in {"nan", "none", ""}:
        return None
    try:
        dt = date.fromisoformat(str(data_str).strip()[:10])
        iso = dt.isocalendar()
        return f"{iso.year:04d}-W{iso.week:02d}"
    except (ValueError, TypeError):
        return None


def _normalizar_tipo(tipo) -> str:
    """Normaliza o tipo de chamado SAMU para identificador sem acentos/espaços."""
    if not tipo or str(tipo).strip().lower() in {"nan", "none", ""}:
        return "nao_informado"
    # Remove acentos comuns e substitui espaços/hífens por underscore.
    t = str(tipo).strip().upper()
    for de, para in [("Á","A"),("Â","A"),("Ã","A"),("É","E"),("Ê","E"),
                     ("Í","I"),("Ó","O"),("Ô","O"),("Ú","U"),("Ç","C")]:
        t = t.replace(de, para)
    t = re.sub(r"[\s\-/]+", "_", t)
    t = re.sub(r"[^A-Z0-9_]", "", t)
    return t.lower() or "nao_informado"


def _agregar(registros: list[dict]) -> list[dict]:
    """Conta chamados por bairro, semana e tipo de emergência."""
    grupos: dict[tuple, int] = defaultdict(int)
    for r in registros:
        municipio = str(r.get("municipio") or "").strip().upper()
        if municipio not in {"RECIFE", ""}:
            continue  # filtra apenas Recife
        periodo = _periodo_semana(r.get("data"))
        if not periodo:
            continue
        bairro = str(r.get("bairro") or "nao_informado").strip().upper()
        tipo   = _normalizar_tipo(r.get("tipo"))
        grupos[(periodo, bairro, tipo)] += 1

    return [
        {
            "territorio":      "Recife",
            "bairro":          bairro,
            "indicador":       f"samu_{tipo}",
            "periodo":         periodo,
            "valor":           count,
        }
        for (periodo, bairro, tipo), count in sorted(grupos.items())
    ]


def _baixar_ano(ano: int) -> list[dict] | None:
    """Tenta baixar o CSV do SAMU para o ano informado. Retorna None se indisponível."""
    dataset_id = f"{_DATASET_PREFIXO}-{ano}"
    try:
        r = get(f"{CKAN_RECIFE}/action/package_show", params={"id": dataset_id})
        resultado = r.json()
        if not resultado.get("success"):
            return None
        recursos = resultado["result"].get("resources", [])
        csvs = [rc for rc in recursos if rc.get("format","").upper() == "CSV" and rc.get("url")]
        if not csvs:
            return None
        resposta = get(csvs[0]["url"])
        try:
            texto = resposta.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = resposta.content.decode("latin-1")
        df = pd.read_csv(StringIO(texto), sep=None, engine="python")
        linhas = dataframe_para_registros(df)
        logger.info("SAMU %d: %d linhas baixadas", ano, len(linhas))
        return linhas
    except Exception as e:
        logger.warning("SAMU %d indisponível: %s", ano, type(e).__name__)
        return None


def pipeline_samu(db):
    """Baixa os chamados SAMU dos últimos ANOS_RECENTES anos e agrega por semana/bairro/tipo."""
    logger.info("Iniciando pipeline SAMU Recife")

    ano_atual = date.today().year
    todos: list[dict] = []

    for ano in range(ano_atual, ano_atual - ANOS_RECENTES - 1, -1):
        linhas = _baixar_ano(ano)
        if linhas:
            todos.extend(linhas)
        if len({r.get("data","")[:4] for r in todos if r.get("data")}) >= ANOS_RECENTES:
            break

    if not todos:
        raise RuntimeError("SAMU: nenhuma linha baixada para nenhum ano disponível.")

    agregados = _agregar(todos)
    if not agregados:
        raise RuntimeError("SAMU: nenhum registro de Recife com data e tipo válidos.")

    salvar_json_local("samu_recife", agregados)

    carregar_documentos(
        db["recife_samu"],
        "dados_abertos_recife",
        agregados,
        "chamados_samu_semanais",
        "Recife",
        campos_chave=("indicador", "periodo", "bairro"),
    )
    logger.info("SAMU concluído: %d grupos agregados", len(agregados))
