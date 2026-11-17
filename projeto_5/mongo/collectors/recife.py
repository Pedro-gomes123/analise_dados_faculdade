"""Coleta e agrega notificações de arboviroses do portal Dados Abertos Recife (CKAN).

Por que CKAN Recife e não dados.gov.br?
- O portal nacional dados.gov.br (SINAN/SVS) retorna HTTP 401 desde 2026
  para download de datasets de arboviroses.
- O Dados Abertos Recife publica notificações locais com bairro e semana
  epidemiológica — granularidade ideal para o projeto.
- O portal usa CKAN (Comprehensive Knowledge Archive Network), que tem
  API REST padronizada para busca e listagem de recursos.

Por que agregar (não armazenar registros individuais)?
- LGPD: dados de saúde são sensíveis. O projeto não precisa de informações
  pessoais (nome, endereço, CPF) — apenas contagens por bairro/semana.
- Redução de volume: de dezenas de milhares de notificações para centenas
  de grupos agregados, sem perda de informação epidemiológica.
"""

import logging
import re
# defaultdict: acumula contagens por chave sem verificar existência.
from collections import defaultdict
from datetime import datetime
from io import StringIO

# pandas + StringIO: leitura de CSV com detecção automática de separador.
import pandas as pd

from mongo.config import CKAN_RECIFE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, get, salvar_json_local

logger = logging.getLogger(__name__)


def _valor(registro, *nomes):
    """Busca o primeiro campo não-vazio em um registro, independente de case.

    Normaliza as chaves para minúsculo antes de comparar, pois os CSVs do
    CKAN Recife misturam colunas em MAIÚSCULO e minúsculo dependendo do ano.
    """
    # Indexa todas as chaves do registro em minúsculo para busca case-insensitive.
    chaves = {str(chave).strip().lower(): chave for chave in registro}
    for nome in nomes:
        chave = chaves.get(nome.lower())
        if chave is not None:
            valor = registro.get(chave)
            if valor is not None and str(valor).strip() not in {"", "nan", "None"}:
                return valor
    return None


def _recife(registro):
    """Verifica se um registro de notificação pertence ao município de Recife.

    Estratégia defensiva: aceita se pelo menos um dos três critérios bater
    (código IBGE, nome do município, UF) sem contradição nos demais.
    Isso evita tanto falsos positivos (outros Reciфes em outros estados)
    quanto falsos negativos (formatos diferentes do mesmo município).
    """
    municipio = str(_valor(registro, "MUNICIPIO", "NM_MUNICIP", "municipio") or "").strip()
    codigo = re.sub(r"\D", "", str(_valor(
        registro, "ID_MUNICIP", "CO_MUN_NOT", "COD_MUNICIPIO"
    ) or "").split(".")[0])  # remove casas decimais ("261160.0" → "261160")
    uf = str(_valor(registro, "SG_UF_NOT", "SG_UF", "UF") or "").strip().upper()

    # 261160 e 2611606 são o mesmo município (com e sem dígito verificador IBGE).
    codigo_recife = codigo in {"261160", "2611606"}
    nome_recife   = municipio.casefold() in {"recife", "recife - pe"}
    uf_pe         = uf in {"PE", "26", "PERNAMBUCO"}

    # Aceita se: (código ou nome de Recife) E (UF é PE ou UF está ausente)
    # E (nome não contradiz o código, se ambos presentes).
    return (codigo_recife or nome_recife) and (not uf or uf_pe) and (
        not municipio or nome_recife or codigo_recife
    )


def _agravo(registro):
    """Mapeia o código CID-10 do agravo para o nome padronizado do projeto.

    Diferentes versões dos CSVs usam código CID (A90, A92.0) ou texto livre
    ("dengue", "DENGUE", "dengue hemorrágica"). Trata ambos para robustez.

    Mapeamento CID-10:
    A90/A91 → dengue  |  A92.0 → chikungunya  |  U06.9 → zika
    """
    codigo = str(_valor(registro, "ID_AGRAVO", "agravo") or "").strip().upper()
    # Remove espaços internos que alguns exports incluem ("A 90" → "A90").
    codigo = re.sub(r"\s+", "", codigo)
    mapeamento = {
        "A90":   "dengue",
        "A91":   "dengue",         # dengue hemorrágica — agrupado em dengue
        "A92.0": "chikungunya",
        "U06.9": "zika",
    }
    if codigo in mapeamento:
        return mapeamento[codigo]

    # Fallback: busca texto livre para cobrir CSVs que não usam CID.
    texto = codigo.casefold()
    for chave in ("dengue", "zika", "chikungunya", "chik"):
        if chave in texto:
            return "chikungunya" if chave == "chik" else chave
    return None  # agravo desconhecido — descartado pelo chamador


def _periodo(registro):
    """Extrai o período em formato ISO "YYYY-WNN" a partir de campos SINAN/CKAN.

    Tenta SEM_NOT (semana de notificação) primeiro, depois SEM_PRI (semana
    dos primeiros sintomas), e por último deriva a semana a partir de DT_NOTIFIC.
    """
    semana = _valor(registro, "SEM_NOT", "SEMANA_EPIDEMIOLOGICA", "SEM_PRI")
    ano    = _valor(registro, "NU_ANO",  "ANO", "NU_ANO_NOT")
    if semana is not None:
        # Remove tudo que não for dígito para lidar com "202644", "44", "044".
        digitos = re.sub(r"\D", "", str(semana))
        try:
            if len(digitos) >= 6:
                # Formato "YYYYWW": ex "202644" → "2026-W44"
                return f"{digitos[:4]}-W{int(digitos[-2:]):02d}"
            if ano is not None:
                # Semana e ano separados: ex semana=44, ano=2026 → "2026-W44"
                return f"{int(float(ano)):04d}-W{int(float(semana)):02d}"
        except (ValueError, OverflowError):
            return None

    # Último recurso: calcula semana ISO a partir da data de notificação.
    data = _valor(registro, "DT_NOTIFIC", "DT_SIN_PRI", "data")
    if data:
        texto = str(data).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"):
            try:
                dt = datetime.strptime(texto, fmt)
                semana_iso = dt.isocalendar()
                return f"{semana_iso.year:04d}-W{semana_iso.week:02d}"
            except ValueError:
                pass
    return None


def agregar_arboviroses_recife(registros):
    """Agrega notificações de Recife em contagens semanais por agravo e bairro.

    Por que usar NU_NOTIFIC para deduplicar?
    O SINAN pode conter múltiplas fichas para o mesmo caso (atualizações).
    Usar o número de notificação como chave no set garante contagem única.
    Registros sem número de notificação ("sem_id") são contados separadamente.
    """
    agregados = defaultdict(lambda: {"ids": set(), "sem_id": 0})
    for registro in registros:
        if not isinstance(registro, dict) or not _recife(registro):
            continue
        agravo  = _agravo(registro)
        periodo = _periodo(registro)
        if not agravo or not periodo:
            continue  # descarta registros sem agravo ou período identificável

        bairro = str(_valor(registro, "NM_BAIRRO", "NOBAIINF", "bairro") or "nao_informado").strip()
        chave  = (agravo, periodo, bairro)

        notificacao = _valor(registro, "NU_NOTIFIC", "ID_NOTIFICACAO")
        if notificacao is None:
            agregados[chave]["sem_id"] += 1
        else:
            agregados[chave]["ids"].add(str(notificacao).strip())

    return [
        {
            "territorio": "Recife",
            "bairro": bairro,
            "indicador": agravo,
            "periodo": periodo,
            "valor": len(valores["ids"]) + valores["sem_id"],
        }
        for (agravo, periodo, bairro), valores in sorted(agregados.items())
    ]


def _carregar_recurso(url, formato):
    """Baixa e parseia um recurso CKAN (CSV ou JSON).

    CSV: decodificado como UTF-8-sig (remove BOM) com fallback para latin-1.
         sep=None detecta automaticamente ";" ou "," como separador.
    JSON: pode retornar lista direta ou dict com resultados em "result"/"records"/"data".
    """
    resposta = get(url)
    if formato == "CSV":
        try:
            texto = resposta.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = resposta.content.decode("latin-1")
        quadro = pd.read_csv(StringIO(texto), sep=None, engine="python")
        return dataframe_para_registros(quadro)

    # JSON: extrai a lista de registros de qualquer estrutura de resposta.
    conteudo = resposta.json()
    if isinstance(conteudo, list):
        return [item for item in conteudo if isinstance(item, dict)]
    if isinstance(conteudo, dict):
        # Tenta extrair a lista de "result", "records" ou "data" (padrões comuns).
        for chave in ("result", "records", "data"):
            if isinstance(conteudo.get(chave), list):
                return [item for item in conteudo[chave] if isinstance(item, dict)]
        return [conteudo]  # o próprio dict é o registro único
    return []


def pipeline_recife_arboviroses(db):
    """Busca e processa datasets de arboviroses do CKAN Recife.

    Estratégia de busca dinâmica:
    Em vez de hardcodar o ID do dataset, fazemos uma busca por palavras-chave
    (dengue, zika, chikungunya). Isso torna o coletor mais resiliente a
    mudanças de ID ou adição de novos datasets com os mesmos dados.
    O primeiro recurso CSV ou JSON com dados válidos de Recife vence.
    """
    logger.info("Iniciando pipeline de arboviroses Dados Abertos Recife")

    # package_search: busca datasets por texto livre no CKAN.
    # rows=50: retorna até 50 datasets para garantir que encontramos o correto.
    resposta = get(
        f"{CKAN_RECIFE}/action/package_search",
        params={"q": "dengue zika chikungunya", "rows": 50},
    )
    resultado = resposta.json()
    if not resultado.get("success"):
        raise RuntimeError("O portal CKAN Recife não confirmou a busca.")

    datasets = resultado.get("result", {}).get("results", [])
    if not isinstance(datasets, list):
        raise RuntimeError("CKAN Recife retornou lista de datasets inválida.")

    # Itera todos os datasets e recursos até encontrar um válido.
    for dataset in datasets:
        for recurso in dataset.get("resources", []):
            formato = str(recurso.get("format") or "").strip().upper()
            if formato not in {"CSV", "JSON"} or not recurso.get("url"):
                continue  # ignora formatos não suportados (PDF, XLS, etc.)

            try:
                linhas = _carregar_recurso(recurso["url"], formato)
                agregados = agregar_arboviroses_recife(linhas)
            except Exception as erro:
                logger.error(
                    "Falha ao baixar/validar recurso CKAN id=%s nome=%s tipo=%s",
                    dataset.get("id"), recurso.get("name"), type(erro).__name__,
                )
                continue

            if not agregados:
                logger.info(
                    "Recurso CKAN sem registros de Recife com agravo e período válidos: %s",
                    recurso.get("name"),
                )
                continue

            # Adiciona metadados do CKAN para rastreabilidade.
            for agregado in agregados:
                agregado.update({
                    "dataset_id": dataset.get("id"),
                    "recurso_nome": recurso.get("name"),
                })

            salvar_json_local("dados_abertos_recife_arboviroses", agregados)

            # Chave de idempotência: (indicador, periodo, bairro) identifica
            # cada contagem semanal por agravo e bairro de forma única.
            carregar_documentos(
                db["recife_arboviroses"],
                "dados_abertos_recife",
                agregados,
                "arboviroses_agregadas_semanais",
                "Recife",
                campos_chave=("indicador", "periodo", "bairro"),
            )
            logger.info("Arboviroses Recife concluído: %d grupos agregados", len(agregados))
            # return logo após o primeiro recurso válido — não processa mais datasets.
            return

    raise RuntimeError(
        "CKAN Recife não forneceu recurso CSV/JSON com registros identificáveis "
        "de Recife, agravo conhecido, semana e bairro. Nenhum registro foi salvo."
    )
