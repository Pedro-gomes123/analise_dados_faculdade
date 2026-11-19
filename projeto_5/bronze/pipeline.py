"""Exporta snapshots das coleções MongoDB para as tabelas bronze no SQL Server.

Responsabilidade da camada bronze na arquitetura medallion:
- Receber documentos do MongoDB exatamente como estão, sem nenhuma
  transformação de negócio. O bronze é um "data lake" relacional —
  preserva o histórico bruto para auditoria e reprocessamento.
- Serializar documentos BSON para JSON usando `json_util.dumps`, que
  trata tipos Python incompatíveis com JSON nativo (datetime → $date,
  ObjectId → $oid, Decimal128 → $numberDecimal).
- Garantir idempotência via MERGE ON _id: re-executar não duplica dados.

O campo `_id` nos documentos MongoDB é um SHA-256 gerado na coleta
a partir da chave de negócio de cada coleção (ex: estacao+lida_em para
meteorologia). Isso garante que o mesmo evento nunca gera dois documentos.
"""

import logging
from datetime import datetime, timezone

# json_util do PyMongo serializa tipos BSON (datetime, ObjectId, Decimal128)
# que o módulo json nativo do Python não suporta. É necessário para preservar
# timestamps com timezone nas colunas payload_json do bronze.
from bson import json_util

logger = logging.getLogger(__name__)

# Mapeamento fixo: nome da coleção MongoDB → tabela bronze de destino no SQL Server.
# A ordem não importa — cada coleção é processada independentemente.
# Adicionar uma nova fonte: basta incluir o par aqui e criar a tabela no DDL.
COLECOES_BRONZE = {
    "inmet_estacoes":              "bronze.inmet_estacoes",
    "openmeteo_horario":           "bronze.openmeteo_horario",
    "openmeteo_historico":         "bronze.openmeteo_historico",
    "nasa_power_horario":          "bronze.nasa_power_horario",
    "recife_arboviroses":          "bronze.recife_arboviroses",
    "recife_defesa_civil":         "bronze.recife_defesa_civil",
    "sinan_animais_peconhentos":   "bronze.sinan_animais_peconhentos",
    "recife_samu":                 "bronze.recife_samu",
    "recife_acidentes_transito":   "bronze.recife_acidentes_transito",
}


def _export_collection(db, collection_name: str, tabela: str, writer, exported_at: datetime) -> dict:
    """Lê todos os documentos de uma coleção e faz upsert na tabela bronze.

    Por que exportar TODOS os documentos (find({}) sem filtro)?
    O MERGE da bronze usa a cláusula WHEN NOT MATCHED THEN INSERT — ignora
    documentos cujo _id já existe. Exportar tudo garante que documentos
    adicionados desde a última execução sejam incluídos sem precisar rastrear
    o delta manualmente.

    Por que dois campos JSON (payload_json e documento_json)?
    - payload_json: apenas o campo "payload" do documento (os dados da API).
      Usado pela silver para transformação — estrutura mais limpa.
    - documento_json: o documento MongoDB completo (inclui _id, ingestao_ts, etc.).
      Permite auditoria e recuperação completa do estado original.

    Args:
        db: pymongo.Database — banco do MongoDB.
        collection_name: nome da coleção MongoDB de origem.
        tabela: nome da tabela bronze de destino ("bronze.openmeteo_horario", etc.).
        writer: BronzeSqlWriter com conexão ao SQL Server aberta.
        exported_at: timestamp UTC desta execução (registrado no log bronze).

    Returns:
        dict com estatísticas: colecao, tabela, documentos lidos, inseridos.
    """
    collection = db[collection_name]
    # find({}) sem projeção: carrega todos os documentos com todos os campos.
    # Para coleções grandes (>100k docs) considerar cursor com batch_size.
    documents = list(collection.find({}))
    if not documents:
        logger.info("Coleção vazia, nenhuma linha inserida: %s", collection_name)
        return {"colecao": collection_name, "tabela": tabela, "documentos": 0, "inseridos": 0}

    rows = []
    for doc in documents:
        # Normaliza o timezone do campo ingestao_ts antes de exportar.
        # PyMongo pode retornar datetimes sem tz se o driver não configurou UTC.
        ingestao_ts = doc.get("ingestao_ts")
        if isinstance(ingestao_ts, datetime) and ingestao_ts.tzinfo is None:
            # datetime naive assume UTC (é a convenção do projeto).
            ingestao_ts = ingestao_ts.replace(tzinfo=timezone.utc)
        elif isinstance(ingestao_ts, datetime):
            ingestao_ts = ingestao_ts.astimezone(timezone.utc)
        else:
            ingestao_ts = None

        payload = doc.get("payload")
        rows.append(
            {
                # str(_id): converte ObjectId para string para armazenar em NVARCHAR.
                "_id": str(doc.get("_id", "")),
                "fonte":        doc.get("fonte"),
                "tipo_dado":    doc.get("tipo_dado"),
                "municipio":    doc.get("municipio"),
                "ingestao_ts":  ingestao_ts,
                # json_util.dumps: serializa payload com suporte a datetime/ObjectId.
                # ensure_ascii=False: mantém caracteres acentuados sem escapar (reduz tamanho).
                "payload_json": (
                    json_util.dumps(payload, ensure_ascii=False)
                    if "payload" in doc
                    else None
                ),
                # Documento completo serializado para auditoria.
                "documento_json": json_util.dumps(doc, ensure_ascii=False),
            }
        )

    inseridos = writer.upsert(collection_name, tabela, rows, exported_at)
    logger.info(
        "Exportação bronze: coleção=%s documentos=%d inseridos=%d tabela=%s",
        collection_name, len(rows), inseridos, tabela,
    )
    return {"colecao": collection_name, "tabela": tabela, "documentos": len(rows), "inseridos": inseridos}


def pipeline_bronze(db, writer=None, exported_at=None) -> list[dict]:
    """Exporta todas as coleções MongoDB para as tabelas bronze do SQL Server.

    Idempotência: pode ser re-executado quantas vezes for necessário.
    O MERGE garante que documentos já exportados não sejam duplicados.

    Gerenciamento de conexão:
    Se `writer` não for fornecido, abre uma conexão SQL Server automaticamente
    via `BronzeSqlWriter` e a fecha no finally. Se for fornecido (ex: em testes),
    o chamador é responsável pelo ciclo de vida da conexão.

    Args:
        db: pymongo.Database — banco do MongoDB com as coleções de coleta.
        writer: BronzeSqlWriter pré-inicializado (opcional; útil em testes).
        exported_at: Timestamp UTC da exportação. Se None, usa o momento atual.

    Returns:
        Lista de dicts com estatísticas por coleção exportada.
    """
    # Importação local: evita importação circular no topo do módulo
    # (bronze depende de silver.database para a conexão SQL).
    from bronze.sql_writer import BronzeSqlWriter
    from silver.database.sql_server import conectar_sql_server

    # Garante que exported_at seja UTC, independente do fuso do servidor.
    exported_at = exported_at or datetime.now(timezone.utc)
    if exported_at.tzinfo is None:
        exported_at = exported_at.replace(tzinfo=timezone.utc)
    exported_at = exported_at.astimezone(timezone.utc)

    # owns_writer controla se este pipeline fecha a conexão ao final.
    owns_writer = writer is None
    if owns_writer:
        connection = conectar_sql_server()
        writer = BronzeSqlWriter(connection)
        # aplicar_ddl: cria schema bronze e tabelas se ainda não existirem.
        # Idempotente — seguro re-executar em cada run.
        writer.aplicar_ddl()

    logger.info("Início da exportação Bronze em %s", exported_at.isoformat())
    results = []
    try:
        # Processa cada coleção independentemente — falha em uma não para as demais.
        for collection_name, tabela in COLECOES_BRONZE.items():
            results.append(_export_collection(db, collection_name, tabela, writer, exported_at))
    finally:
        # Fecha a conexão somente se foi aberta por este pipeline.
        if owns_writer:
            writer.connection.close()

    total_docs = sum(r["documentos"] for r in results)
    total_ins  = sum(r["inseridos"]  for r in results)
    logger.info(
        "Resumo Bronze: coleções=%d documentos=%d inseridos=%d horário=%s",
        len(results), total_docs, total_ins, exported_at.isoformat(),
    )
    return results
