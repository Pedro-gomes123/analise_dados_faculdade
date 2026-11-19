"""Re-exporta tudo dos módulos especializados.

Mantido apenas para compatibilidade com imports antigos.
Prefira importar diretamente de http, normalizers ou storage.
"""

from mongo.utils.http import get
from mongo.utils.normalizers import (
    normalizar_registro,
    para_numero,
    primeiro_valor,
    serializar,
    utc_datetime,
)
from mongo.utils.storage import dataframe_para_registros, salvar_json_local

__all__ = [
    "get",
    "normalizar_registro",
    "para_numero",
    "primeiro_valor",
    "serializar",
    "utc_datetime",
    "dataframe_para_registros",
    "salvar_json_local",
]
