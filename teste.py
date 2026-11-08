"""
VigiaClima-Recife — pipelines de ingestão para MongoDB Atlas.

Coleções criadas em operacional_db:
- inmet_estacoes
- inmet_observacoes
- openmeteo_horario
- recife_arboviroses
- s2id_desastres
- sinan_animais_peconhentos

Instalação:
    python3 -m pip install pymongo requests pandas openpyxl
    python3 -m pip install pysus  # opcional, para a fonte SINAN

Segurança:
- Preencha MONGO_PASSWORD no código, mas não publique este arquivo em repositório público.
- Se a senha tiver caracteres especiais, quote_plus faz a codificação da credencial.
"""

import hashlib
import json
import warnings
from datetime import date, timedelta, datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

warnings.filterwarnings("ignore", message="Unverified HTTPS")

# ============================================================
# CONFIGURAÇÃO
# ============================================================

MONGO_USER = "operado_mongo_json"
MONGO_PASSWORD = "pdededreffddrexc12431241"  # não compartilhe este arquivo
MONGO_HOSTS = (
    "ac-hydwtcu-shard-00-00.xlxwro1.mongodb.net:27017,"
    "ac-hydwtcu-shard-00-01.xlxwro1.mongodb.net:27017,"
    "ac-hydwtcu-shard-00-02.xlxwro1.mongodb.net:27017"
)
MONGO_OPTIONS = (
    "?ssl=true&replicaSet=atlas-6me506-shard-0&authSource=admin"
)
MONGO_DATABASE = "operacional_db"

RAW = Path("raw")
RAW.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "VigiaClima-Recife/1.0 (explorador-APIs)"}
LAT, LON = -8.05, -34.90
GEOCODIGO_RECIFE = 2611606
INMET_BASE = "https://apitempo.inmet.gov.br"
ESTACAO_RECIFE = "A301"
CKAN_RECIFE = "https://dados.recife.pe.gov.br/api/3"
CKAN_GOV = "https://dados.gov.br/dados/api/3"


def construir_uri_mongo() -> str:
    """Monta a URI codificando usuário e senha corretamente."""
    if not MONGO_PASSWORD or MONGO_PASSWORD == "COLE_A_SENHA_ATUAL_AQUI":
        raise ValueError("Preencha MONGO_PASSWORD no início do arquivo.")
    user = quote_plus(MONGO_USER)
    password = quote_plus(MONGO_PASSWORD)
    return f"mongodb://{user}:{password}@{MONGO_HOSTS}/{MONGO_OPTIONS}"


def get(url, **kwargs):
    """GET com timeout, cabeçalhos e validação HTTP."""
    response = requests.get(
        url,
        timeout=60,
        headers=HEADERS,
        **kwargs,
    )
    print(f"GET {response.url}")
    print(f" -> HTTP {response.status_code}, {len(response.content)} bytes")
    response.raise_for_status()
    return response


def serializar(valor):
    """Converte valores do pandas/numpy/data para tipos aceitos pelo BSON."""
    if valor is None:
        return None
    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except (ValueError, AttributeError):
            pass
    if pd.isna(valor) if not isinstance(valor, (dict, list, tuple)) else False:
        return None
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def normalizar_registro(registro):
    if isinstance(registro, dict):
        return {str(k): serializar(v) for k, v in registro.items()}
    return {"valor": serializar(registro)}


def salvar_json_local(nome, dados):
    caminho = RAW / f"{nome}.json"
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"Arquivo local salvo: {caminho}")


def carregar_documentos(collection, fonte, registros, tipo_dado, municipio="Recife"):
    """
    Grava um documento por registro.
    _id determinístico evita duplicar o mesmo registro em execuções futuras.
    O payload mantém os campos originais retornados pela fonte.
    """
    agora = datetime.now(timezone.utc)
    operacoes = []
    quantidade = 0

    for registro in registros:
        payload = normalizar_registro(registro)
        assinatura = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        identificador = hashlib.sha256(f"{fonte}|{tipo_dado}|{assinatura}".encode("utf-8")).hexdigest()

        doc = {
            "_id": identificador,
            "fonte": fonte,
            "tipo_dado": tipo_dado,
            "municipio": municipio,
            "ingestao_ts": agora,
            "payload": payload,
        }
        operacoes.append(
            UpdateOne({"_id": identificador}, {"$setOnInsert": doc}, upsert=True)
        )
        quantidade += 1

    if not operacoes:
        print(f"⚠️ Nenhum registro para inserir em {collection.name}.")
        return {"recebidos": 0, "novos": 0}

    resultado = collection.bulk_write(operacoes, ordered=False)
    novos = resultado.upserted_count
    print(
        f"✅ {collection.name}: {quantidade} registros recebidos; "
        f"{novos} novos; {quantidade - novos} já existiam."
    )
    return {"recebidos": quantidade, "novos": novos}


def dataframe_para_registros(df):
    return [
        normalizar_registro(registro)
        for registro in df.to_dict(orient="records")
    ]


# ============================================================
# PIPELINE 1 — INMET
# ============================================================

def pipeline_inmet(db):
    print("\n" + "=" * 65 + "\nPIPELINE INMET\n" + "=" * 65)

    # Estações automáticas
    resposta = get(f"{INMET_BASE}/estacoes/T")
    estacoes = resposta.json()
    salvar_json_local("inmet_estacoes", estacoes)

    estacoes_pe = [
        e for e in estacoes
        if str(e.get("SG_ESTADO", "")).upper() == "PE"
    ]
    carregar_documentos(
        db["inmet_estacoes"], "inmet", estacoes_pe, "estacao_automatica", "Pernambuco"
    )

    # Observações horárias da estação A301
    fim = date.today()
    inicio = fim - timedelta(days=2)
    resposta_dados = get(
        f"{INMET_BASE}/estacao/{inicio.isoformat()}/{fim.isoformat()}/{ESTACAO_RECIFE}"
    )
    dados = resposta_dados.json()
    salvar_json_local(f"inmet_{ESTACAO_RECIFE}", dados)

    if isinstance(dados, list):
        registros = dados
    elif isinstance(dados, dict):
        # Alguns endpoints podem retornar um objeto único.
        registros = [dados]
    else:
        registros = []

    carregar_documentos(
        db["inmet_observacoes"], "inmet", registros, "observacao_horaria", "Recife"
    )


# ============================================================
# PIPELINE 2 — OPEN-METEO
# ============================================================

def pipeline_openmeteo(db):
    print("\n" + "=" * 65 + "\nPIPELINE OPEN-METEO\n" + "=" * 65)

    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "precipitation,temperature_2m,relative_humidity_2m,surface_pressure",
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "America/Recife",
    }
    resposta = get("https://api.open-meteo.com/v1/forecast", params=params)
    dados = resposta.json()
    salvar_json_local("openmeteo", dados)

    hourly = dados.get("hourly", {})
    tempos = hourly.get("time", [])
    registros = []
    for i, tempo in enumerate(tempos):
        registro = {
            "data_hora": tempo,
            "latitude": dados.get("latitude"),
            "longitude": dados.get("longitude"),
            "timezone": dados.get("timezone"),
            "precipitacao_mm": (hourly.get("precipitation") or [None] * len(tempos))[i],
            "temperatura_C": (hourly.get("temperature_2m") or [None] * len(tempos))[i],
            "umidade_pct": (hourly.get("relative_humidity_2m") or [None] * len(tempos))[i],
            "pressao_hPa": (hourly.get("surface_pressure") or [None] * len(tempos))[i],
        }

        # Acumulados calculados usando a janela disponível até aquela hora.
        inicio_24 = max(0, i - 23)
        inicio_72 = max(0, i - 71)
        chuva = hourly.get("precipitation", [])
        registro["chuva_24h_mm"] = (
            sum(x for x in chuva[inicio_24:i + 1] if x is not None)
            if chuva else None
        )
        registro["chuva_72h_mm"] = (
            sum(x for x in chuva[inicio_72:i + 1] if x is not None)
            if chuva else None
        )
        registros.append(registro)

    carregar_documentos(
        db["openmeteo_horario"], "open_meteo", registros, "meteorologia_horaria"
    )


# ============================================================
# PIPELINE 3 — DADOS ABERTOS RECIFE / ARBOVIROSES
# ============================================================

def pipeline_recife_arboviroses(db):
    print("\n" + "=" * 65 + "\nPIPELINE DADOS ABERTOS RECIFE\n" + "=" * 65)

    resposta = get(
        f"{CKAN_RECIFE}/action/package_search",
        params={"q": "dengue zika chikungunya", "rows": 10},
    )
    resultado = resposta.json()
    if not resultado.get("success"):
        raise RuntimeError("O portal CKAN Recife não confirmou a busca.")

    datasets = resultado.get("result", {}).get("results", [])
    registros_finais = []

    # Tenta recursos CSV/JSON; segue para outros recursos se um falhar.
    for dataset in datasets:
        recursos = dataset.get("resources", [])
        for recurso in recursos:
            formato = str(recurso.get("format") or "").upper()
            if formato not in {"CSV", "JSON"} or not recurso.get("url"):
                continue

            try:
                print(f"Recurso: {dataset.get('title')} / {recurso.get('name')} ({formato})")
                resp = get(recurso["url"])
                if formato == "CSV":
                    try:
                        df = pd.read_csv(StringIO(resp.content.decode("utf-8-sig")), sep=None, engine="python")
                    except UnicodeDecodeError:
                        df = pd.read_csv(StringIO(resp.content.decode("latin-1")), sep=None, engine="python")
                    registros = dataframe_para_registros(df.head(100))
                else:
                    conteudo = resp.json()
                    if isinstance(conteudo, list):
                        registros = [normalizar_registro(x) for x in conteudo[:100]]
                    elif isinstance(conteudo, dict):
                        registros = [normalizar_registro(conteudo)]
                    else:
                        registros = []

                for registro in registros:
                    registro["_dataset_id"] = dataset.get("id")
                    registro["_dataset_titulo"] = dataset.get("title")
                    registro["_recurso_nome"] = recurso.get("name")
                if registros:
                    registros_finais = registros
                    break
            except Exception as erro:
                print(f"⚠️ Recurso não pôde ser carregado: {erro}")

        if registros_finais:
            break

    if not registros_finais:
        print("⚠️ Nenhum recurso CSV/JSON disponível foi baixado.")
        return

    salvar_json_local("dados_abertos_recife_arboviroses", registros_finais)
    carregar_documentos(
        db["recife_arboviroses"],
        "dados_abertos_recife",
        registros_finais,
        "arboviroses",
    )


# ============================================================
# PIPELINE 4 — DADOS.GOV.BR / S2ID
# ============================================================

def pipeline_s2id(db):
    print("\n" + "=" * 65 + "\nPIPELINE S2ID / DADOS.GOV.BR\n" + "=" * 65)

    termos = ["s2id desastre", "calamidade publica", "defesa civil emergencia"]
    encontrados = {}

    for termo in termos:
        try:
            resposta = get(
                f"{CKAN_GOV}/action/package_search",
                params={"q": termo, "rows": 5},
            )
            resultado = resposta.json()
            if resultado.get("success"):
                for dataset in resultado.get("result", {}).get("results", []):
                    encontrados[dataset.get("id")] = dataset
        except Exception as erro:
            print(f"⚠️ Busca '{termo}' falhou: {erro}")

    registros_finais = []
    for dataset in encontrados.values():
        for recurso in dataset.get("resources", []):
            formato = str(recurso.get("format") or "").upper()
            if formato not in {"CSV", "JSON", "XLSX"} or not recurso.get("url"):
                continue
            try:
                print(f"Recurso: {dataset.get('title')} / {recurso.get('name')} ({formato})")
                resp = get(recurso["url"])
                if formato == "CSV":
                    try:
                        df = pd.read_csv(StringIO(resp.content.decode("utf-8-sig")), sep=None, engine="python")
                    except UnicodeDecodeError:
                        df = pd.read_csv(StringIO(resp.content.decode("latin-1")), sep=None, engine="python")
                elif formato == "JSON":
                    conteudo = resp.json()
                    if isinstance(conteudo, list):
                        registros = [normalizar_registro(x) for x in conteudo[:200]]
                    elif isinstance(conteudo, dict):
                        registros = [normalizar_registro(conteudo)]
                    else:
                        registros = []
                    df = None
                else:
                    df = pd.read_excel(BytesIO(resp.content))

                if df is not None:
                    registros = dataframe_para_registros(df.head(200))

                for registro in registros:
                    registro["_dataset_id"] = dataset.get("id")
                    registro["_dataset_titulo"] = dataset.get("title")
                    registro["_recurso_nome"] = recurso.get("name")

                # Filtra PE se existir uma coluna de UF; se não, mantém amostra original.
                if registros:
                    chaves = {str(k).lower(): k for k in registros[0].keys()}
                    col_uf = next((chaves[k] for k in ("uf", "estado", "sg_uf") if k in chaves), None)
                    if col_uf:
                        registros_pe = [
                            r for r in registros
                            if str(r.get(col_uf, "")).upper() in {"PE", "PERNAMBUCO"}
                        ]
                        if registros_pe:
                            registros = registros_pe

                    registros_finais = registros
                    break
            except Exception as erro:
                print(f"⚠️ Recurso não pôde ser carregado: {erro}")
        if registros_finais:
            break

    if not registros_finais:
        print("⚠️ Não foi possível baixar um recurso de desastres nesta execução.")
        return

    salvar_json_local("s2id_desastres", registros_finais)
    carregar_documentos(
        db["s2id_desastres"], "dados_gov_s2id", registros_finais, "desastres"
    )


# ============================================================
# PIPELINE 5 — PySUS / DATASUS / SINAN
# ============================================================

def pipeline_sinan(db):
    print("\n" + "=" * 65 + "\nPIPELINE PySUS / SINAN\n" + "=" * 65)

    try:
        from pysus.online_data.sinan import SINAN
    except ImportError:
        print("⚠️ PySUS não instalado. Para habilitar: python3 -m pip install pysus")
        return

    try:
        sinan = SINAN()
        agravos = sinan.list_diseases()
        print("Agravos disponíveis consultados.")

        alvo = next(
            (
                a for a in agravos
                if "pe" in str(a).lower()
                and ("anim" in str(a).lower() or "onhe" in str(a).lower())
            ),
            None,
        )
        if alvo is None:
            alvo = next(
                (
                    a for a in agravos
                    if "animais peconhentos" in str(a).lower()
                    or "animais peçonhentos" in str(a).lower()
                ),
                None,
            )

        if alvo is None:
            print("⚠️ Agravo de animais peçonhentos não encontrado automaticamente.")
            print("Confira a lista retornada por sinan.list_diseases() e ajuste o alvo.")
            return

        ano = date.today().year - 1
        print(f"Baixando {alvo}, ano {ano}, UF PE...")
        df = sinan.download(alvo, year=ano, uf="PE")
        registros = dataframe_para_registros(df.head(100))
        salvar_json_local("pysus_animais_peconhentos_PE", registros)

        carregar_documentos(
            db["sinan_animais_peconhentos"],
            "pysus_sinan",
            registros,
            "notificacoes_animais_peconhentos",
            "Pernambuco",
        )
    except Exception as erro:
        print(f"⚠️ Falha no pipeline PySUS/SINAN: {erro}")


# ============================================================
# EXECUÇÃO
# ============================================================

def main():
    uri = construir_uri_mongo()
    print("=" * 65)
    print("VigiaClima-Recife — ingestão das fontes para MongoDB Atlas")
    print("=" * 65)

    with MongoClient(uri, serverSelectionTimeoutMS=15000) as cliente:
        cliente.admin.command("ping")
        print("✅ Conexão com MongoDB Atlas estabelecida.")
        db = cliente[MONGO_DATABASE]

        pipelines = [
            ("INMET", pipeline_inmet),
            ("Open-Meteo", pipeline_openmeteo),
            ("Dados Abertos Recife", pipeline_recife_arboviroses),
            ("S2ID / dados.gov.br", pipeline_s2id),
            ("PySUS / SINAN", pipeline_sinan),
        ]

        for nome, funcao in pipelines:
            try:
                funcao(db)
            except Exception as erro:
                print(f"❌ Pipeline {nome} falhou: {type(erro).__name__}: {erro}")

        print("\n" + "=" * 65)
        print("Execução finalizada. Confira as coleções no MongoDB Compass.")
        print("=" * 65)


if __name__ == "__main__":
    main()
