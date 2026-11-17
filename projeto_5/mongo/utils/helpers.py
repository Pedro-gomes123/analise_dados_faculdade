"""Funções utilitárias compartilhadas pelos coletores.

Este módulo concentra operações repetidas em todos os coletores:
chamadas HTTP, normalização de tipos, parsing de datas e serialização
para o MongoDB. Centralizar aqui evita duplicação de código e garante
comportamento consistente entre fontes diferentes.
"""

import json
import logging
import re
# math: usado para detectar NaN e Inf que o float() não descarta,
# mas que causariam erros ao persistir no MongoDB ou SQL Server.
from datetime import date, datetime, time, timezone
from urllib.parse import urlsplit

# pandas: biblioteca de análise de dados. Usamos aqui apenas para
# ler CSVs (read_csv com detecção automática de separador) e para
# detectar valores NA em tipos como numpy.float64 que o Python nativo
# não reconhece como None. É a ferramenta padrão para lidar com dados
# tabulares heterogêneos vindos de portais de dados abertos.
import pandas as pd

# requests: biblioteca HTTP mais popular do ecossistema Python.
# Escolhida por ser síncrona (simples para pipelines sequenciais),
# robusta e ter excelente suporte a streaming, sessões e retries.
# Alternativas async (httpx, aiohttp) só valeriam se as chamadas
# fossem paralelizadas, o que não é o caso aqui.
import requests

from mongo.config import HEADERS, RAW_DIR

logger = logging.getLogger(__name__)


def get(url, **kwargs):
    """Executa uma requisição GET com timeout e validação HTTP.

    Centraliza as chamadas HTTP para garantir:
    - Timeout fixo de 60 s (evita travar o pipeline indefinidamente).
    - User-Agent padronizado (boas práticas com APIs abertas).
    - Loga URL sem query string (evita vazar tokens/parâmetros no log).
    - Lança HTTPError para qualquer status >= 400 (fail-fast).
    """
    response = requests.get(
        url,
        timeout=60,       # 60 s: suficiente para APIs lentas, evita travar o pipeline
        headers=HEADERS,  # identifica o projeto para o servidor da API
        **kwargs,         # aceita params=, json=, etc. passados pelo chamador
    )

    # Remove query string do log para não expor tokens ou chaves de API
    # que possam estar nos parâmetros da URL.
    partes = urlsplit(url)
    url_segura = f"{partes.scheme}://{partes.netloc}{partes.path}"
    logger.info("GET %s -> HTTP %s (%s bytes)", url_segura, response.status_code, len(response.content))

    # raise_for_status() lança requests.HTTPError para 4xx/5xx.
    # Isso propaga a falha para o chamador (coletor) que decide o que fazer
    # (encerrar pipeline, tentar fallback, etc.).
    response.raise_for_status()

    return response


def serializar(valor):
    """Converte valores heterogêneos para tipos compatíveis com o MongoDB.

    Pandas e NumPy retornam tipos próprios (numpy.int64, numpy.float64,
    pandas.NaT) que o driver pymongo não sabe serializar. Esta função
    garante que tudo se torne tipos Python nativos antes de gravar.

    Regras de conversão:
    - numpy scalar  → Python nativo via .item()
    - pandas NA/NaT → None
    - datetime sem tz → UTC explícito (MongoDB armazena em UTC)
    - date           → datetime meia-noite UTC (MongoDB não tem tipo date)
    - demais         → retorna sem alteração
    """
    if valor is None:
        return None

    # NumPy scalars (int64, float32, etc.) têm o método .item() que extrai
    # o valor Python nativo equivalente. Sem isso, pymongo levantaria TypeError.
    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except (ValueError, AttributeError):
            pass

    # dict, list e tuple são tipos MongoDB nativos — passam direto.
    if isinstance(valor, (dict, list, tuple)):
        return valor

    # pd.isna() detecta NaN, None, pandas.NaT e numpy.nan de forma unificada.
    # Envolvemos em try/except porque pd.isna() lança ValueError para arrays.
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    # Datetimes sem timezone são ambíguos (local? UTC?). Assumimos UTC porque
    # todas as APIs do projeto usam UTC ou UTC-3 (Brasília), e o MongoDB
    # armazena tudo em UTC de qualquer forma.
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)

    # date não tem hora → converte para meia-noite UTC para manter tipo uniforme.
    if isinstance(valor, date):
        return datetime.combine(valor, time.min, tzinfo=timezone.utc)

    return valor


def normalizar_registro(registro):
    """Normaliza um registro recebido de qualquer fonte de dados.

    Aplica serializar() em todos os valores e garante que as chaves sejam
    strings Python. APIs diferentes retornam chaves como bytes, inteiros ou
    objetos não-string — str(chave) cobre esses casos sem perder dados.
    """
    if isinstance(registro, dict):
        return {
            str(chave): serializar(valor)
            for chave, valor in registro.items()
        }

    # Se o registro não é um dict (ex: valor escalar de um CSV),
    # embrulha em {"valor": ...} para manter a estrutura uniforme.
    return {"valor": serializar(registro)}


def salvar_json_local(nome, dados):
    """Salva cópia local dos dados para fins de depuração.

    Não faz parte do fluxo de produção — serve para inspecionar
    manualmente o que foi retornado pela API sem precisar fazer
    uma nova requisição. Os arquivos ficam em mongo/data/raw/.

    default=str no json.dumps garante que tipos não-serializáveis
    (datetime, ObjectId) sejam convertidos para string em vez de
    levantar TypeError.
    """
    caminho = RAW_DIR / f"{nome}.json"

    caminho.write_text(
        json.dumps(
            dados,
            ensure_ascii=False,  # preserva acentos (português)
            indent=2,            # JSON legível por humanos
            default=str,         # converte datetime, etc. para string
        ),
        encoding="utf-8",
    )

    logger.info("Arquivo JSON de depuração salvo: %s", caminho.name)


def dataframe_para_registros(df):
    """Converte um DataFrame pandas em lista de dicts normalizados.

    df.to_dict(orient="records") transforma cada linha em um dict,
    mas os valores ainda podem ter tipos NumPy. normalizar_registro()
    converte todos para tipos Python nativos compatíveis com MongoDB.
    """
    return [
        normalizar_registro(registro)
        for registro in df.to_dict(orient="records")
    ]


def para_numero(valor):
    """Converte para float, tratando formatos numéricos heterogêneos.

    Lida com três situações comuns em dados brasileiros:
    1. Decimal com vírgula: "1.234,56" → 1234.56
    2. Sentinela NASA POWER: -999.0 (tratado pelo chamador)
    3. Strings como "nan", "inf" que o float() converte mas que
       são inválidas como medições — retorna None.

    math.isnan e math.isinf: float("nan") e float("inf") são valores
    Python válidos, mas representam ausência de dado. Precisamos de
    math para detectá-los porque isinstance(float("nan"), float) == True.
    """
    import math
    valor = serializar(valor)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace(" ", "")
        # Detecta decimal brasileiro "1.234,56" pela presença de vírgula:
        # remove pontos de milhar e substitui vírgula por ponto decimal.
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        valor = texto
    try:
        resultado = float(valor)
        # math.isnan e math.isinf descartam valores que passaram pelo float()
        # mas não representam medições reais (ex: float("nan"), float("inf")).
        return None if (math.isnan(resultado) or math.isinf(resultado)) else resultado
    except (TypeError, ValueError):
        return None


def utc_datetime(data, hora=None):
    """Interpreta texto de data/hora em vários formatos e devolve datetime UTC.

    Cada API retorna datas em um formato diferente:
    - Open-Meteo: ISO 8601 "2026-11-15T12:00"
    - INMET:      "2026-11-15" + "1200" (separados)
    - CKAN CSV:   "15/11/2026" (formato brasileiro)
    - NASA POWER: "YYYYMMDDH" (tratado pelo coletor antes de chamar esta função)

    Aceita datetime já pronto (retorna com timezone UTC), string de data
    com hora opcional separada, ou ISO 8601 com e sem timezone.

    Datetimes sem timezone são assumidos UTC — convenção uniforme do projeto.
    """
    if isinstance(data, datetime):
        resultado = data
    else:
        texto = str(data or "").strip()
        if not texto:
            return None
        resultado = None
        # Tenta os formatos mais comuns primeiro (ISO, americano, brasileiro).
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                resultado = datetime.strptime(texto, formato)
                break
            except ValueError:
                continue
        if resultado is None:
            # Fallback para ISO 8601 com hora e possível timezone.
            # "Z" é substituído por "+00:00" porque fromisoformat não aceita "Z"
            # no Python < 3.11.
            try:
                resultado = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            except ValueError:
                return None

    # Aplica componente de hora separado (usado pelo INMET que envia
    # data e hora em campos distintos "DT_MEDICAO" / "HR_MEDICAO").
    if hora is not None and not isinstance(data, datetime):
        hora_texto = str(hora or "").strip()
        # Aceita "1200", "12:00" ou "12 00" via regex flexível.
        match = re.search(r"(\d{1,2})\s*:?\s*(\d{2})", hora_texto)
        if match:
            try:
                resultado = resultado.replace(
                    hour=int(match.group(1)), minute=int(match.group(2)),
                    second=0, microsecond=0,
                )
            except ValueError:
                return None

    # Normaliza timezone: sem tz → assume UTC; com tz → converte para UTC.
    if resultado.tzinfo is None:
        resultado = resultado.replace(tzinfo=timezone.utc)
    return resultado.astimezone(timezone.utc)


def primeiro_valor(registro, *nomes):
    """Retorna o primeiro campo não-vazio entre vários aliases de coluna.

    Diferentes endpoints do mesmo fornecedor (ex: INMET) às vezes usam
    nomes de campo diferentes para a mesma variável. Esta função abstrai
    essa variação, tentando cada alias em ordem até encontrar um valor.

    Exemplo:
        primeiro_valor(estacao, "CD_ESTACAO", "CD_WSI")
        → retorna "A301" se CD_ESTACAO existir, ou o CD_WSI como fallback.
    """
    for nome in nomes:
        valor = registro.get(nome)
        if valor is not None and str(valor).strip() not in {"", "None", "nan"}:
            return valor
    return None
