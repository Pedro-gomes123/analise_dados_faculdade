"""Coleta atendimentos da Defesa Civil do Recife via Dados Abertos Recife (CKAN).

Por que este coletor substitui o s2id.py (dados.gov.br)?
- O portal dados.gov.br/S2ID passou a retornar HTTP 401 (Não Autorizado)
  em 2026, impossibilitando o download dos datasets nacionais de desastres.
- O Dados Abertos Recife (portal CKAN da Prefeitura) publica os atendimentos
  da Defesa Civil local com granularidade de bairro — mais relevante para
  o projeto que foca em Recife — e continua acessível sem autenticação.

Por que agregar por mês e não por ocorrência individual?
- Os CSVs publicados não contêm dados pessoais dos solicitantes, apenas
  o tipo de ocorrência e o bairro. Mesmo assim, agregamos mensalmente
  para consistência com a abordagem LGPD do restante do projeto.
"""

import logging
import re
# defaultdict: acumula contagens sem verificar existência de chave a cada iteração.
from collections import defaultdict
from io import StringIO

# pandas + StringIO: leitura de CSV com detecção automática de separador (sep=None).
# Muitos CSVs de portais brasileiros usam ";" como separador ou têm BOM UTF-8.
# O engine="python" é necessário para sep=None.
import pandas as pd

from mongo.config import CKAN_RECIFE
from mongo.database.mongodb import carregar_documentos
from mongo.utils.helpers import dataframe_para_registros, get, salvar_json_local

logger = logging.getLogger(__name__)

# ID do dataset no portal CKAN da Prefeitura do Recife.
# Esse identificador é estável — não muda quando o dataset é atualizado.
DATASET_ID = "registro-de-atendimentos-da-defesa-civil"

# Número de anos mais recentes a baixar.
# O dataset publica um CSV por ano; baixar os 2 mais recentes cobre
# o ano atual (que pode estar incompleto) e o anterior (completo).
ANOS_RECENTES = 2

# Dicionário de meses em português para converter "novembro" → "11".
# Usado porque o campo "Mês" no CSV da Defesa Civil vem por extenso.
_MESES = {
    "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
    "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
    "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
}


def _carregar_csv(url: str) -> list[dict]:
    """Baixa um CSV via HTTP e retorna lista de dicts normalizados.

    Tenta decodificar como UTF-8-sig primeiro (remove BOM dos CSVs do Windows),
    depois como latin-1 (fallback para CSVs com caracteres especiais brasileiros).
    sep=None + engine="python": detecta automaticamente ";" ou "," como separador.
    """
    resposta = get(url)
    try:
        texto = resposta.content.decode("utf-8-sig")  # UTF-8 com BOM (Windows)
    except UnicodeDecodeError:
        texto = resposta.content.decode("latin-1")    # fallback para ISO-8859-1
    df = pd.read_csv(StringIO(texto), sep=None, engine="python")
    return dataframe_para_registros(df)


def _agregar(registros: list[dict]) -> list[dict]:
    """Conta atendimentos por tipo de ocorrência, bairro e mês.

    Por que período mensal e não semanal?
    A Defesa Civil do Recife publica dados com granularidade mensal (mês por
    extenso em português). Manter "YYYY-MM" como período preserva a resolução
    original sem inventar granularidade não existente.
    """
    grupos: dict[tuple, int] = defaultdict(int)
    for r in registros:
        ano = str(r.get("Ano") or "").strip()
        if not ano or ano.casefold() in {"nan", "none"}:
            continue  # registro sem ano não pode ser classificado por período

        mes_txt = str(r.get("Mês") or "").strip().casefold()
        # Converte nome do mês ("novembro") para número ("11").
        # "00" como fallback sinaliza mês desconhecido sem descartar o registro.
        mes = _MESES.get(mes_txt, "00")

        # Prioriza "Ocorrencia" (tipo de evento), fallback para "Solicitacao".
        tipo = str(r.get("Ocorrencia") or r.get("Solicitacao") or "").strip()
        # re.sub normaliza espaços múltiplos em um único espaço.
        tipo = re.sub(r"\s+", " ", tipo) or "nao_informado"

        bairro  = str(r.get("Bairro") or "").strip() or "nao_informado"
        periodo = f"{ano}-{mes}"   # formato YYYY-MM (ex: "2026-11")

        grupos[(tipo, periodo, bairro)] += 1

    return [
        {
            "territorio": "Recife",
            "bairro": bairro,
            "tipo_ocorrencia": tipo,
            "periodo": periodo,
            "valor": count,
        }
        for (tipo, periodo, bairro), count in sorted(grupos.items())
    ]


def pipeline_defesa_civil(db):
    """Carrega os atendimentos recentes da Defesa Civil do Recife e agrega por mês.

    Estratégia de seleção de CSVs:
    1. Busca o dataset pelo ID fixo (package_show).
    2. Filtra recursos com formato CSV que tenham URL.
    3. Deduplica por nome (o portal publica CSVs duplicados às vezes).
    4. Ordena por nome (os nomes incluem o ano: "2025", "2026") e pega os ANOS_RECENTES mais recentes.
    """
    logger.info("Iniciando pipeline Defesa Civil Recife")

    # CKAN package_show retorna metadados completos do dataset incluindo a lista
    # de recursos (arquivos) com URLs de download.
    resposta = get(
        f"{CKAN_RECIFE}/action/package_show",
        params={"id": DATASET_ID},
    )
    resultado = resposta.json()
    if not resultado.get("success"):
        raise RuntimeError(
            f"CKAN Recife não retornou o dataset de Defesa Civil (id={DATASET_ID!r})."
        )

    recursos = resultado["result"].get("resources", [])
    # Filtra apenas CSVs com URL válida — ignora outros formatos (PDF, XLS, etc.).
    csvs = [
        r for r in recursos
        if str(r.get("format") or "").upper() == "CSV" and r.get("url")
    ]

    # Deduplicar por nome: o portal às vezes republica o mesmo arquivo com IDs diferentes.
    # vistos é um set que rastreia nomes já adicionados.
    vistos: set[str] = set()
    csvs_unicos = []
    for r in csvs:
        nome = r.get("name", "")
        if nome not in vistos:
            vistos.add(nome)
            csvs_unicos.append(r)

    # Ordena por nome (decrescente) para que os anos mais recentes venham primeiro,
    # depois pega apenas os ANOS_RECENTES primeiros.
    csvs_recentes = sorted(
        csvs_unicos, key=lambda r: r.get("name", ""), reverse=True
    )[:ANOS_RECENTES]

    if not csvs_recentes:
        raise RuntimeError("Defesa Civil: nenhum recurso CSV encontrado no dataset.")

    todos: list[dict] = []
    for recurso in csvs_recentes:
        try:
            linhas = _carregar_csv(recurso["url"])
            todos.extend(linhas)
            logger.info(
                "Defesa Civil carregado: %s (%d linhas)",
                recurso.get("name"), len(linhas),
            )
        except Exception as erro:
            # Falha em um arquivo não para o pipeline — tenta os outros.
            logger.error(
                "Falha ao carregar recurso Defesa Civil nome=%s tipo=%s",
                recurso.get("name"), type(erro).__name__,
            )

    if not todos:
        raise RuntimeError("Defesa Civil: nenhuma linha carregada dos CSVs selecionados.")

    agregados = _agregar(todos)
    if not agregados:
        raise RuntimeError("Defesa Civil: nenhum registro com ano e tipo identificável.")

    salvar_json_local("defesa_civil_recife", agregados)

    # Chave de idempotência: (tipo_ocorrencia, periodo, bairro) identifica
    # unicamente cada contagem mensal. Re-execuções atualizam sem duplicar.
    carregar_documentos(
        db["recife_defesa_civil"],
        "dados_abertos_recife",
        agregados,
        "atendimentos_defesa_civil_mensais",
        "Recife",
        campos_chave=("tipo_ocorrencia", "periodo", "bairro"),
    )
    logger.info(
        "Defesa Civil concluído: %d grupos de %d registros totais.",
        len(agregados), len(todos),
    )
