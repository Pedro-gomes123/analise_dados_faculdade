"""Conexão e persistência no MongoDB Atlas.

Por que MongoDB na camada de coleta?
- Schema flexível: cada API retorna payloads com estruturas diferentes.
  O MongoDB aceita qualquer dict sem precisar definir schema antecipadamente.
- Idempotência: o _id SHA-256 garante que re-execuções não duplicam dados.
- Caching da coleta bruta: o MongoDB preserva o snapshot original da API,
  isolando a camada de coleta das transformações de limpeza (bronze/silver).
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone

# pymongo: driver oficial do MongoDB para Python. Suporta operações bulk
# (bulk_write), upsert atômico (UpdateOne com upsert=True) e conexão com
# MongoDB Atlas (cloud) via URI mongodb+srv://.
from pymongo import MongoClient, UpdateOne

from mongo.utils.normalizers import normalizar_registro

logger = logging.getLogger(__name__)


def conectar_mongodb():
    """Conecta ao MongoDB Atlas usando a variável de ambiente MONGODB_URI.

    Por que Atlas (cloud) e não MongoDB local?
    - O projeto usa Azure SQL Server para as camadas analíticas. Um MongoDB
      Atlas free tier é suficiente para o volume de dados operacionais e
      evita manter infraestrutura local.
    - serverSelectionTimeoutMS=15000: falha rápido se o Atlas estiver
      inacessível, em vez de travar o pipeline por minutos.
    """
    uri = os.environ.get("MONGODB_URI")

    if not uri:
        raise RuntimeError(
            "A variável de ambiente MONGODB_URI não foi configurada."
        )

    cliente = MongoClient(
        uri,
        # Timeout de 15 s para selecionar um servidor replica set do Atlas.
        # Sem isso, a conexão pode travar por até 30 s no padrão do driver.
        serverSelectionTimeoutMS=15000,
    )

    # ping valida que a conexão realmente funciona antes de prosseguir.
    # MongoClient é lazy — sem o ping, erros de credencial só aparecem
    # na primeira operação real.
    try:
        cliente.admin.command("ping")
    except Exception:
        cliente.close()
        raise

    logger.info("Conexão com MongoDB Atlas estabelecida.")

    return cliente


def carregar_documentos(
    collection,
    fonte,
    registros,
    tipo_dado,
    municipio="Recife",
    campos_chave=None,
):
    """Persiste registros no MongoDB com upsert idempotente baseado em SHA-256.

    Por que SHA-256 como _id e não ObjectId?
    - ObjectId é gerado aleatoriamente: re-executar o pipeline criaria
      documentos duplicados para a mesma observação.
    - SHA-256 é determinístico: o mesmo registro sempre gera o mesmo _id,
      portanto upsert (UpdateOne com upsert=True) nunca duplica dados.
    - A chave SHA-256 é calculada sobre `campos_chave` (ex: estacao + lida_em),
      que identifica de forma única cada medição de negócio.

    Por que bulk_write em vez de insert_many?
    - bulk_write processa múltiplos documentos em uma única viagem de rede,
      reduzindo latência especialmente contra o Atlas (cloud).
    - UpdateOne com upsert=True: insere se _id não existe, atualiza se já existe.
      Isso garante que novos campos adicionados ao payload sejam propagados
      em re-execuções sem duplicar o documento.
    """
    agora = datetime.now(timezone.utc)
    registros = list(registros)
    por_id = {}  # dict para deduplicar _ids antes de enviar ao MongoDB

    for registro in registros:
        # normalizar_registro converte tipos NumPy/Pandas para Python nativo
        # e garante que todos os campos sejam serializáveis pelo pymongo.
        payload = normalizar_registro(registro)

        # Extrai apenas os campos de chave para o hash (ex: estacao + lida_em).
        # Se campos_chave não for definido, usa o payload inteiro como chave
        # (menos eficiente mas seguro para coleções sem chave natural).
        chave = (
            {campo: payload.get(campo) for campo in campos_chave}
            if campos_chave
            else payload
        )
        # Valida que todos os campos de chave têm valor — sem isso o SHA-256
        # ficaria idêntico para registros distintos com campos nulos.
        if campos_chave and any(valor is None for valor in chave.values()):
            raise ValueError(
                f"Registro sem campo necessário para chave idempotente: {campos_chave}"
            )

        # json.dumps com sort_keys=True garante que a mesma chave sempre
        # gera o mesmo JSON independente da ordem dos campos no dicionário.
        # default=str serializa datetime para string ISO antes do hash.
        assinatura = json.dumps(
            chave,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        # SHA-256: inclui fonte e tipo_dado no hash para evitar colisões entre
        # coleções diferentes que possam ter o mesmo valor de chave de negócio.
        identificador = hashlib.sha256(
            f"{fonte}|{tipo_dado}|{assinatura}".encode("utf-8")
        ).hexdigest()

        # Estrutura padrão de todos os documentos do projeto:
        # - _id: SHA-256 determinístico (chave de idempotência)
        # - fonte: qual API gerou o dado (openmeteo, nasa_power, etc.)
        # - tipo_dado: natureza do dado (meteorologia_horaria, arboviroses_agregadas, etc.)
        # - municipio: granularidade geográfica do dado
        # - ingestao_ts: quando o dado foi coletado (UTC)
        # - payload: o dado em si, com todos os campos normalizados
        documento = {
            "_id": identificador,
            "fonte": fonte,
            "tipo_dado": tipo_dado,
            "municipio": municipio,
            "ingestao_ts": agora,
            "payload": payload,
        }

        # por_id deduplicar: se dois registros tiverem a mesma chave de negócio
        # dentro do mesmo batch (ex: dois CSVs com a mesma linha), apenas o
        # último prevalece. Na prática isso não ocorre, mas é uma defesa extra.
        por_id[identificador] = documento

    # Constrói uma lista de operações bulk: cada UpdateOne faz upsert por _id.
    # $set atualiza todos os campos exceto _id. $setOnInsert garante que _id
    # não seja sobrescrito (embora isso nunca ocorra num upsert por _id).
    operacoes = [
        UpdateOne(
            {"_id": identificador},
            {
                "$set": {chave: valor for chave, valor in documento.items() if chave != "_id"},
                "$setOnInsert": {"_id": identificador},
            },
            upsert=True,
        )
        for identificador, documento in por_id.items()
    ]

    if not operacoes:
        logger.info("Nenhum registro para inserir em %s.", collection.name)
        return {"recebidos": 0, "novos": 0}

    # ordered=False: continua processando mesmo se um documento falhar.
    # Em um batch de 2.000 documentos, um erro isolado não para tudo.
    resultado = collection.bulk_write(operacoes, ordered=False)

    novos = resultado.upserted_count

    logger.info(
        "%s: %d registros recebidos, %d IDs únicos, %d novos, %d atualizados.",
        collection.name,
        len(registros),
        len(operacoes),
        novos,
        resultado.modified_count,
    )

    return {
        "recebidos": len(registros),
        "novos": novos,
        "ids_unicos": len(operacoes),
    }
