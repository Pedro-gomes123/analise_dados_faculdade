"""Configurações globais e variáveis de ambiente do módulo mongo.

Centralizar as configurações aqui garante que qualquer alteração de
parâmetro (coordenadas, URLs de API, banco de dados) se propague para
todos os coletores sem precisar editar múltiplos arquivos.
"""

import os
from pathlib import Path

# python-dotenv: lê o arquivo .env do projeto e injeta as variáveis no
# os.environ. Usar um .env evita colocar credenciais diretamente no código
# (que poderia vazar via git). O arquivo .env está no .gitignore.
from dotenv import load_dotenv

# Resolve o caminho do .env a partir do arquivo atual, independente de onde
# o script é invocado (via IDE, terminal ou CI/CD).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Nome do banco MongoDB. O default "operacional_db" é usado em desenvolvimento;
# em produção o valor vem do .env para isolar ambientes.
MONGO_DATABASE = os.environ.get("MONGODB_DATABASE", "operacional_db")

# Diretório local para salvar cópias brutas das respostas de API.
# Usado apenas para depuração — não faz parte do fluxo de produção.
# parents=True + exist_ok=True cria a pasta sem erro se já existir.
RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Cabeçalho HTTP enviado em todas as requisições.
# O User-Agent identifica o projeto para os servidores externos, o que é
# boas práticas de uso de APIs abertas e ajuda no diagnóstico de logs do servidor.
HEADERS = {
    "User-Agent": "VigiaClima-Recife/1.0 (explorador-APIs)"
}

# Coordenadas do ponto de referência de Recife usadas pelas APIs climáticas.
# Open-Meteo e NASA POWER trabalham com um único ponto lat/lon; escolhemos o
# centro urbano de Recife para representar toda a cidade no modelo climático.
LAT, LON = -8.05, -34.90

# Código IBGE de 7 dígitos do município de Recife. Usado para filtrar
# notificações epidemiológicas (dengue, zika, etc.) por município.
GEOCODIGO_RECIFE = 2611606

# Base da API do INMET (Instituto Nacional de Meteorologia).
# A rota /estacoes/T retorna todas as estações automáticas do Brasil sem token.
# A rota /estacao/{datas}/{codigo} retorna observações horárias — requer token.
INMET_BASE = "https://apitempo.inmet.gov.br"

# Código da estação automática do INMET mais próxima de Recife/PE.
# A301 fica no bairro do Curado, zona oeste do Recife.
ESTACAO_RECIFE = "A301"

# Token opcional do INMET. Sem ele, /estacao retorna HTTP 204 (sem conteúdo).
# Para obter: acesse portal.inmet.gov.br, cadastre-se e gere o token.
# O valor None desativa as observações horárias sem quebrar o pipeline de estações.
INMET_TOKEN = os.environ.get("INMET_TOKEN")

# URL base da API CKAN do portal de Dados Abertos do Recife.
# CKAN (Comprehensive Knowledge Archive Network) é o software open-source usado
# pela Prefeitura do Recife para publicar seus datasets.
CKAN_RECIFE = "https://dados.recife.pe.gov.br/api/3"
