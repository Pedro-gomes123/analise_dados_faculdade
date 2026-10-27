"""Funções utilitárias compartilhadas pelos coletores."""

import json
from datetime import date, datetime

import pandas as pd
import requests

from src.config import HEADERS, RAW_DIR


def get(url, **kwargs):
    """Executa uma requisição GET com timeout e validação HTTP."""

    response = requests.get(
        url,
        timeout=60,
        headers=HEADERS,
        **kwargs,
    )

    print(f"GET {response.url}")
    print(
        f" -> HTTP {response.status_code}, "
        f"{len(response.content)} bytes"
    )

    response.raise_for_status()

    return response


def serializar(valor):
    """Converte valores para tipos compatíveis com o MongoDB."""

    if valor is None:
        return None

    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except (ValueError, AttributeError):
            pass

    if isinstance(valor, (dict, list, tuple)):
        return valor

    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(valor, (datetime, date)):
        return valor.isoformat()

    return valor


def normalizar_registro(registro):
    """Normaliza um registro recebido de uma fonte."""

    if isinstance(registro, dict):
        return {
            str(chave): serializar(valor)
            for chave, valor in registro.items()
        }

    return {"valor": serializar(registro)}


def salvar_json_local(nome, dados):
    """Salva uma cópia local para depuração."""

    caminho = RAW_DIR / f"{nome}.json"

    caminho.write_text(
        json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"Arquivo local salvo: {caminho}")


def dataframe_para_registros(df):
    """Converte um DataFrame em uma lista de dicionários."""

    return [
        normalizar_registro(registro)
        for registro in df.to_dict(orient="records")
    ]