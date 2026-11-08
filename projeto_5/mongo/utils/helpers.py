"""Funções utilitárias compartilhadas pelos coletores."""

import json
import logging
import re
from datetime import date, datetime, time, timezone
from urllib.parse import urlsplit

import pandas as pd
import requests

from mongo.config import HEADERS, RAW_DIR

logger = logging.getLogger(__name__)


def get(url, **kwargs):
    """Executa uma requisição GET com timeout e validação HTTP."""

    response = requests.get(
        url,
        timeout=60,
        headers=HEADERS,
        **kwargs,
    )

    partes = urlsplit(url)
    url_segura = f"{partes.scheme}://{partes.netloc}{partes.path}"
    logger.info("GET %s -> HTTP %s (%s bytes)", url_segura, response.status_code, len(response.content))

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

    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)

    if isinstance(valor, date):
        return datetime.combine(valor, time.min, tzinfo=timezone.utc)

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

    logger.info("Arquivo JSON de depuração salvo: %s", caminho.name)


def dataframe_para_registros(df):
    """Converte um DataFrame em uma lista de dicionários."""

    return [
        normalizar_registro(registro)
        for registro in df.to_dict(orient="records")
    ]


def para_numero(valor):
    """Converte números JSON/CSV, inclusive decimais brasileiros, para float."""
    valor = serializar(valor)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        valor = texto
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def utc_datetime(data, hora=None):
    """Interpreta data/hora e devolve datetime UTC; horários sem fuso são UTC."""
    if isinstance(data, datetime):
        resultado = data
    else:
        texto = str(data or "").strip()
        if not texto:
            return None
        resultado = None
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                resultado = datetime.strptime(texto, formato)
                break
            except ValueError:
                continue
        if resultado is None:
            try:
                resultado = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            except ValueError:
                return None

    if hora is not None and not isinstance(data, datetime):
        hora_texto = str(hora or "").strip()
        match = re.search(r"(\d{1,2})\s*:?\s*(\d{2})", hora_texto)
        if match:
            try:
                resultado = resultado.replace(
                    hour=int(match.group(1)), minute=int(match.group(2)),
                    second=0, microsecond=0,
                )
            except ValueError:
                return None

    if resultado.tzinfo is None:
        resultado = resultado.replace(tzinfo=timezone.utc)
    return resultado.astimezone(timezone.utc)


def primeiro_valor(registro, *nomes):
    """Retorna o primeiro campo presente e não vazio entre aliases da origem."""
    for nome in nomes:
        valor = registro.get(nome)
        if valor is not None and str(valor).strip() not in {"", "None", "nan"}:
            return valor
    return None
