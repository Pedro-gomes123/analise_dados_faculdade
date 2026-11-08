
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MONGO_DATABASE = os.environ.get("MONGODB_DATABASE", "operacional_db")

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
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
