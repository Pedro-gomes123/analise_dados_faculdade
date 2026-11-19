"""Normalização de tipos e datas para o MongoDB.

Pandas e NumPy retornam tipos próprios (numpy.int64, NaT) que o pymongo
não sabe serializar. Funções aqui convertem tudo para tipos Python nativos.
"""

import logging
import math
import re
from datetime import date, datetime, time, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def serializar(valor):
    """Converte tipos NumPy/Pandas para tipos Python nativos compatíveis com MongoDB."""
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
    """Aplica serializar() em todos os valores de um dict."""
    if isinstance(registro, dict):
        return {str(chave): serializar(valor) for chave, valor in registro.items()}
    return {"valor": serializar(registro)}


def para_numero(valor):
    """Converte para float tratando decimal brasileiro ("1.234,56") e NaN/Inf."""
    valor = serializar(valor)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        valor = texto
    try:
        resultado = float(valor)
        return None if (math.isnan(resultado) or math.isinf(resultado)) else resultado
    except (TypeError, ValueError):
        return None


def utc_datetime(data, hora=None):
    """Interpreta texto de data/hora em vários formatos e devolve datetime UTC.

    Suporta: ISO 8601, "YYYY-MM-DD", "DD/MM/YYYY", INMET (data + hora separados).
    """
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
    """Retorna o primeiro campo não-vazio entre vários aliases de coluna."""
    for nome in nomes:
        valor = registro.get(nome)
        if valor is not None and str(valor).strip() not in {"", "None", "nan"}:
            return valor
    return None
