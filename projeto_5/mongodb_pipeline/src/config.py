
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env na raiz do projeto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_DATABASE = "operacional_db"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "VigiaClima-Recife/1.0 (explorador-APIs)"
}

LAT, LON = -8.05, -34.90
GEOCODIGO_RECIFE = 2611606

INMET_BASE = "https://apitempo.inmet.gov.br"
ESTACAO_RECIFE = "A301"

CKAN_RECIFE = "https://dados.recife.pe.gov.br/api/3"
CKAN_GOV = "https://dados.gov.br/dados/api/3"
