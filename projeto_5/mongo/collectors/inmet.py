"""Coleta estações meteorológicas e observações horárias da API INMET.

Por que usar o INMET?
- O INMET (Instituto Nacional de Meteorologia) é a fonte oficial de observações
  de estações automáticas do Brasil. Seus dados são medições reais (não modelos),
  tornando-os a referência para validar as reanálises da Open-Meteo e NASA POWER.
- A A301 é a estação INMET em Recife/PE — cobre exatamente o território de interesse.
- A API é REST/JSON sem paginação e retorna dados horários para uma janela de datas.

Por que o token é opcional?
- Endpoints de listagem de estações são públicos (sem token).
- Endpoints de observações exigem token desde 2024, mas o projeto foi estruturado
  para funcionar sem ele: coleta metadados (localização, altitude) mesmo sem token,
  e só falha silenciosamente nas observações (warning, não RuntimeError).
  Isso permite rodar em ambientes de CI sem credenciais INMET configuradas.
"""

import logging
from datetime import date, timedelta

from mongo.config import ESTACAO_RECIFE, INMET_BASE, INMET_TOKEN
from mongo.database.mongodb import carregar_documentos
from mongo.utils.http import get
from mongo.utils.normalizers import para_numero, primeiro_valor, utc_datetime
from mongo.utils.storage import salvar_json_local

logger = logging.getLogger(__name__)


def _normalizar_estacao(estacao):
    """Preserva todos os campos INMET e adiciona aliases com nomes padronizados.

    Por que preservar os campos originais (CD_ESTACAO, VL_LATITUDE, etc.)?
    A camada silver precisa lidar com dois formatos — payload normalizado e
    payload bruto. Preservar os campos originais evita perda de informação
    e permite que a silver funcione com dados coletados antes da normalização.

    Por que `primeiro_valor`?
    A API INMET mudou nomes de campos entre versões (DC_NOME → DC_NOME_ESTACAO,
    VL_LATITUDE → TP_LATITUDE). `primeiro_valor` tenta cada alias em ordem.
    """
    return {
        # Mantém todos os campos originais do INMET para rastreabilidade.
        **estacao,
        # Campos padronizados usados pelo restante do projeto.
        "fonte": "inmet",
        # CD_ESTACAO: código da estação convencional (ex: "A301")
        # CD_WSI: código WIGOS — padrão OMM — para estações mais novas
        "estacao": primeiro_valor(estacao, "CD_ESTACAO", "CD_WSI"),
        "nome": primeiro_valor(estacao, "DC_NOME", "DC_NOME_ESTACAO"),
        # Hierarquia de fallback para o nome do município (campo variou entre versões da API).
        "municipio": primeiro_valor(
            estacao, "NM_MUNICIPIO", "DC_MUNICIPIO", "MUNICIPIO", "municipio"
        ),
        # para_numero: converte string "−8.0597" para float -8.0597.
        # VL_LATITUDE é o nome mais comum; algumas versões usam VL_LATITUDE diretamente.
        "latitude":  para_numero(primeiro_valor(estacao, "VL_LATITUDE")),
        "longitude": para_numero(primeiro_valor(estacao, "VL_LONGITUDE")),
        "situacao":  primeiro_valor(estacao, "CD_SITUACAO", "situacao"),
    }


def _normalizar_observacao(registro, codigo_estacao):
    """Normaliza uma observação horária do INMET para o esquema padrão do projeto.

    Por que preservar os campos originais no spread **registro?
    O INMET retorna dezenas de variáveis meteorológicas (temperatura máxima,
    mínima, bulbo úmido, etc.) que podem ser úteis para análise futura.
    Manter o payload completo no MongoDB evita necessidade de nova coleta.

    Por que retornar None em vez de lançar exceção?
    O chamador filtra None em list comprehension. Registros sem data válida
    são uma ocorrência esperada nos primeiros/últimos horários do INMET.

    Campos de data/hora:
    - DT_MEDICAO: data no formato "AAAA-MM-DD"
    - HR_MEDICAO: hora no formato "HHMM" (ex: "0000" = 00:00 UTC)
    `utc_datetime` aceita ambos os formatos e retorna datetime com tz=UTC.
    """
    # Combina data e hora em um único datetime UTC para facilitar JOINs no SQL.
    data_hora = utc_datetime(
        primeiro_valor(registro, "DT_MEDICAO", "data", "data_hora"),
        primeiro_valor(registro, "HR_MEDICAO", "hora"),
    )
    if data_hora is None:
        return None  # registro sem data/hora válida — descartado pelo chamador

    # Extrai as variáveis com cadeia de fallback por nome de campo.
    # O INMET alterou nomes (CHUVA → PRECIPITACAO_TOTAL) entre versões da API.
    variaveis = {
        "precipitacao_mm": para_numero(primeiro_valor(
            registro, "CHUVA", "PRECIPITACAO_TOTAL", "PRECIPITACAO", "precipitacao_mm"
        )),
        "temperatura_c": para_numero(primeiro_valor(
            registro, "TEMP_INS", "TEM_INS", "TEMP_AR", "TEMPERATURA", "temperatura_c"
        )),
        "umidade_pct": para_numero(primeiro_valor(
            registro, "UMD_INS", "UMID_REL", "UMIDADE", "umidade_pct"
        )),
        # O INMET já retorna pressão em hPa — sem necessidade de conversão.
        "pressao_hpa": para_numero(primeiro_valor(
            registro, "PRE_INS", "PRESSAO_ATMOSFERICA", "PRESSAO", "pressao_hpa"
        )),
    }
    return {
        # Payload bruto completo do INMET para o MongoDB.
        **registro,
        # Campos padronizados adicionados sobre o payload original.
        "fonte":        "inmet",
        "estacao":      primeiro_valor(registro, "CD_ESTACAO") or codigo_estacao,
        "territorio":   "Recife",
        "lida_em":      data_hora,
        # "observado" significa leitura de sensor real, não modelo ou previsão.
        # Distingue esse dado das reanálises (ERA5, MERRA-2) e previsões (open-meteo).
        "natureza_dado": "observado",
        "variaveis":    variaveis,
    }


def pipeline_inmet(db):
    """Coleta lista de estações de PE e as observações recentes da A301.

    Fluxo em duas etapas:
    1. Estações (público, sem token):
       GET /estacoes/T → lista todas as estações automáticas do Brasil.
       Filtra SG_ESTADO == "PE" para obter apenas as pernambucanas.
       Persiste em db["inmet_estacoes"] com chave (estacao).

    2. Observações (requer token, falha silenciosa se ausente):
       GET /estacao/{inicio}/{fim}/{codigo} → observações horárias dos últimos 2 dias.
       Persiste em db["inmet_observacoes"] com chave (estacao, lida_em).

    Por que 2 dias de janela?
    O INMET publica dados com até 1 hora de atraso; 2 dias garante captura
    completa do dia anterior sem risco de lacunas no início do dia atual.
    """
    logger.info("Iniciando pipeline INMET")

    # --- Estações (endpoint público) ----------------------------------------
    # /estacoes/T: "T" = automáticas (Tipo T); "M" = convencionais (manuais).
    resposta = get(f"{INMET_BASE}/estacoes/T")
    estacoes = resposta.json()
    if not isinstance(estacoes, list):
        raise RuntimeError("A API do INMET não retornou uma lista de estações.")

    # Filtra apenas Pernambuco — o endpoint retorna todas as ~600 estações do Brasil.
    estacoes_pe = []
    for estacao in estacoes:
        if not isinstance(estacao, dict):
            continue
        # SG_ESTADO é a sigla do estado (ex: "PE", "SP", "AM").
        if str(estacao.get("SG_ESTADO", "")).strip().upper() != "PE":
            continue
        normalizada = _normalizar_estacao(estacao)
        # Descarta estações sem código — não conseguimos identificá-las como chave.
        if normalizada["estacao"]:
            estacoes_pe.append(normalizada)

    if not estacoes_pe:
        raise RuntimeError("A API do INMET não retornou estações de Pernambuco.")

    salvar_json_local("inmet_estacoes", estacoes_pe)

    # Persiste com chave de idempotência (estacao): re-execução atualiza metadados
    # sem criar duplicatas, caso o INMET corrija coordenadas ou nome de estação.
    carregar_documentos(
        db["inmet_estacoes"],
        "inmet",
        estacoes_pe,
        "estacao_automatica",
        "Pernambuco",
        campos_chave=("estacao",),
    )

    # --- Observações (requer INMET_TOKEN) ------------------------------------
    fim    = date.today()
    inicio = fim - timedelta(days=2)  # janela de 2 dias para garantir completude

    # URL do endpoint de observações: /estacao/{inicio}/{fim}/{codigo_estacao}
    url = (
        f"{INMET_BASE}/estacao/{inicio.isoformat()}/"
        f"{fim.isoformat()}/{ESTACAO_RECIFE}"
    )
    # Token via query param "token" se disponível; sem token a requisição é feita
    # assim mesmo (pode retornar HTTP 204 sem dados).
    kwargs = {"params": {"token": INMET_TOKEN}} if INMET_TOKEN else {}
    resposta_dados = get(url, **kwargs)

    # HTTP 204 = No Content: sem dados para o período (token ausente ou API sem dados).
    if resposta_dados.status_code == 204 or not resposta_dados.content:
        dica = (
            "Configure INMET_TOKEN no .env (portal.inmet.gov.br) para habilitar."
            if not INMET_TOKEN
            else "API sem dados para o período solicitado."
        )
        logger.warning(
            "INMET sem observações para %s entre %s e %s. %s",
            ESTACAO_RECIFE,
            inicio,
            fim,
            dica,
        )
        # Retorno silencioso: coletou estações com sucesso, apenas sem observações.
        return

    dados = resposta_dados.json()
    salvar_json_local(f"inmet_{ESTACAO_RECIFE}", dados)

    # A API pode retornar um dict (1 registro) ou list (múltiplos registros).
    # Normaliza para lista para processamento uniforme.
    if isinstance(dados, dict):
        registros = [dados]
    elif isinstance(dados, list):
        registros = dados
    else:
        raise RuntimeError("A API do INMET retornou observações em formato inválido.")

    # List comprehension com filtro None: descarta observações sem data/hora válida.
    normalizados = [
        observacao
        for registro in registros
        if isinstance(registro, dict)
        for observacao in [_normalizar_observacao(registro, ESTACAO_RECIFE)]
        if observacao is not None
    ]
    if not normalizados:
        raise RuntimeError(
            f"INMET retornou observações sem data/hora válida para {ESTACAO_RECIFE}."
        )

    # Chave (estacao, lida_em): garante uma linha por horário por estação.
    carregar_documentos(
        db["inmet_observacoes"],
        "inmet",
        normalizados,
        "observacao_horaria",
        "Recife",
        campos_chave=("estacao", "lida_em"),
    )
    logger.info("Pipeline INMET concluído")
