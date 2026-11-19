"""Serialização para arquivo local e conversão de DataFrames.

Usado para debug (salvar JSON bruto) e para transformar DataFrames
pandas em listas de dicts normalizados antes de gravar no MongoDB.
"""

import json
import logging

import pandas as pd

from mongo.config import RAW_DIR
from mongo.utils.normalizers import normalizar_registro

logger = logging.getLogger(__name__)


def salvar_json_local(nome, dados):
    """Salva cópia local dos dados em mongo/data/raw/ para depuração."""
    caminho = RAW_DIR / f"{nome}.json"
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Arquivo JSON de depuração salvo: %s", caminho.name)


def dataframe_para_registros(df: pd.DataFrame) -> list[dict]:
    """Converte DataFrame em lista de dicts com tipos Python nativos."""
    return [normalizar_registro(r) for r in df.to_dict(orient="records")]
