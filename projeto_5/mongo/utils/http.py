"""Wrapper HTTP para os coletores.

Centraliza timeout, User-Agent e logging sem expor tokens/parâmetros nas URLs.
"""

import logging
from urllib.parse import urlsplit

import requests

from mongo.config import HEADERS

logger = logging.getLogger(__name__)


def get(url, **kwargs):
    """GET com timeout fixo, User-Agent padronizado e log sem query string."""
    response = requests.get(url, timeout=60, headers=HEADERS, **kwargs)

    partes = urlsplit(url)
    url_segura = f"{partes.scheme}://{partes.netloc}{partes.path}"
    logger.info("GET %s -> HTTP %s (%s bytes)", url_segura, response.status_code, len(response.content))

    response.raise_for_status()
    return response
