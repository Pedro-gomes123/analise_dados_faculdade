"""Escrita idempotente dos documentos MongoDB nas tabelas bronze do SQL Server.

Design
------
A camada bronze recebe documentos do MongoDB exatamente como estão, sem
transformação de negócio. A idempotência é garantida pelo campo `_id`, que
é um SHA-256 gerado pelo `carregar_documentos` do MongoDB a partir da chave
de negócio de cada coleção. Assim, re-execuções da pipeline não duplicam dados.

Por que MERGE com WHEN NOT MATCHED apenas (sem WHEN MATCHED UPDATE)?
O bronze é imutável por design: o dado bruto original não deve ser sobrescrito.
Se a API corrigir um dado histórico, isso resulta em um novo documento no MongoDB
(novo _id) — a versão anterior permanece no bronze como histórico de auditoria.

O `payload_json` armazena o campo `payload` do documento MongoDB serializado
como BSON Extended JSON (`json_util.dumps`), preservando tipos como `datetime`
e `ObjectId` que o JSON nativo não suporta.

Referência dos scripts DDL
--------------------------
sql/bronze/001_bronze_tables.sql — schema bronze + 7 tabelas de dados + ExportacoesLog
"""

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex de validação de nome de tabela: impede SQL injection na cláusula MERGE.
# Aceita apenas letras, dígitos, underscore e ponto (formato "schema.tabela").
# Bloqueia espaços, hífens, aspas e quaisquer outros caracteres usados em ataques.
_TABELA_VALIDA = re.compile(r"^[a-zA-Z0-9_.]+$")

# Path para o script DDL bronze — calculado dinamicamente para funcionar
# independente do diretório de trabalho (CWD) no momento da execução.
# parents[1] sobe dois níveis: sql_writer.py → bronze/ → projeto_5/ → sql/bronze/
SQL_SCRIPTS = (
    Path(__file__).resolve().parents[1] / "sql" / "bronze" / "001_bronze_tables.sql",
)

# Template MERGE para inserção idempotente no bronze.
# WITH (HOLDLOCK): evita race condition entre duas execuções paralelas
# (ex: CI rodando ao mesmo tempo que o cron) — garante atomicidade do MERGE.
# WHEN NOT MATCHED THEN INSERT: documentos existentes são ignorados (imutabilidade bronze).
# CONVERT(datetimeoffset(6), ?): converte string ISO 8601 para o tipo SQL correto.
_MERGE = """\
MERGE {table} WITH (HOLDLOCK) AS tgt
USING (VALUES (?, ?, ?, ?, CONVERT(datetimeoffset(6), ?), ?, ?, CONVERT(datetimeoffset(6), ?)))
    AS src ([_id], fonte, tipo_dado, municipio, ingestao_ts, payload_json, documento_json, exportado_em)
ON tgt.[_id] = src.[_id]
WHEN NOT MATCHED THEN
    INSERT ([_id], fonte, tipo_dado, municipio, ingestao_ts, payload_json, documento_json, exportado_em)
    VALUES (src.[_id], src.fonte, src.tipo_dado, src.municipio, src.ingestao_ts,
            src.payload_json, src.documento_json, src.exportado_em);
"""

# SQL para registrar metadados de cada exportação na tabela de log.
# Permite auditar: quando exportou, quantos documentos, de qual coleção.
_LOG_INSERT = """\
INSERT INTO bronze.ExportacoesLog (colecao, tabela, exportado_em, documentos, inseridos)
VALUES (?, ?, CONVERT(datetimeoffset(6), ?), ?, ?)
"""


def _validar_tabela(tabela: str) -> None:
    """Rejeita nomes de tabela que permitiriam injeção SQL.

    Por que validar aqui e não confiar no chamador?
    O nome da tabela é interpolado diretamente no SQL do _MERGE ({table}).
    pyodbc não parametriza nomes de tabela — só valores. Sem esta validação,
    um nome como "bronze.foo; DROP TABLE bronze.openmeteo_horario --" seria
    executado como SQL livre.

    Aceita apenas letras, dígitos, underscores e ponto (para "schema.tabela").
    Bloqueia espaços, hífens, aspas e outros caracteres usados em ataques.

    Args:
        tabela: Nome da tabela a validar.

    Raises:
        ValueError: Se o nome contiver caracteres não permitidos.
    """
    if not _TABELA_VALIDA.match(tabela):
        raise ValueError(f"Nome de tabela inválido: {tabela!r}")


class BronzeSqlWriter:
    """Adaptador de escrita SQL para a camada bronze.

    Encapsula a lógica de DDL, upsert e logging de exportações.
    Recebe uma conexão pyodbc já aberta e não a fecha — o chamador
    é responsável pelo ciclo de vida da conexão.

    Uso típico (gerenciado pelo pipeline_bronze):
        writer = BronzeSqlWriter(connection)
        writer.aplicar_ddl()
        writer.upsert("coleção", "bronze.tabela", rows, exported_at)
    """

    def __init__(self, connection):
        # connection: objeto pyodbc.Connection — mantido como atributo público
        # para que pipeline_bronze possa fechá-lo após o uso.
        self.connection = connection

    def aplicar_ddl(self, scripts=SQL_SCRIPTS) -> None:
        """Cria o schema bronze e as tabelas se ainda não existirem.

        Divide o SQL em batches pelo delimitador GO e executa um commit por
        batch. O delimitador GO é específico do T-SQL e não é entendido pelo
        driver pyodbc como um único statement — precisa ser tratado no Python.

        Todos os DDLs usam IF OBJECT_ID IS NULL, tornando a re-execução segura.

        Args:
            scripts: Iterable de paths dos arquivos .sql (padrão: SQL_SCRIPTS).

        Raises:
            Exception: Erro de banco; faz rollback e relança.
        """
        cursor = self.connection.cursor()
        try:
            for caminho in scripts:
                script = Path(caminho).read_text(encoding="utf-8")
                # re.split com (?im): ignora case e trata múltiplas linhas.
                # Padrão GO aceita comentários na mesma linha (GO -- cria schema).
                batches = re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script)
                for batch in batches:
                    if batch.strip():
                        cursor.execute(batch)
                        # Commit por batch: se um batch falha, o anterior já está
                        # confirmado. Evita rollback de DDL que não pode ser desfeito.
                        self.connection.commit()
                logger.info("DDL bronze aplicado: %s", Path(caminho).name)
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def upsert(self, colecao: str, tabela: str, rows: list[dict], exportado_em: datetime) -> int:
        """Insere documentos novos na tabela bronze via MERGE; ignora _id já presente.

        O MERGE usa apenas a cláusula WHEN NOT MATCHED — documentos existentes
        não são atualizados, pois o bronze deve preservar o snapshot original.
        O `exportado_em` registra quando o dado saiu do MongoDB para o SQL.

        Por que executemany e não execute em loop?
        executemany envia todos os parâmetros em uma única roundtrip TCP para
        o SQL Server, reduzindo drasticamente o tempo de execução para grandes
        volumes (5-10x mais rápido que execute em loop para 1000+ linhas).

        Args:
            colecao: Nome da coleção MongoDB de origem (para o log).
            tabela: Nome da tabela bronze destino (ex.: "bronze.openmeteo_horario").
            rows: Lista de dicts com chaves: _id, fonte, tipo_dado, municipio,
                ingestao_ts, payload_json, documento_json.
            exportado_em: Timestamp UTC da execução do pipeline.

        Returns:
            Número de linhas processadas (tentadas para inserção).

        Raises:
            ValueError: Se `tabela` contiver caracteres inválidos.
            Exception: Erro de banco; faz rollback e relança.
        """
        # Validação antecipada: falha rápido se o nome da tabela for inválido.
        _validar_tabela(tabela)
        if not rows:
            self._registrar_log(colecao, tabela, exportado_em, 0, 0)
            return 0

        # Converte exported_at para string ISO uma vez (evita conversão por linha).
        ts_export = exportado_em.isoformat()
        # Monta lista de tuplas para executemany — uma por documento.
        # ingestao_ts.isoformat(): converte datetime para string ISO 8601 com tz.
        params = [
            (
                r.get("_id"),
                r.get("fonte"),
                r.get("tipo_dado"),
                r.get("municipio"),
                r.get("ingestao_ts").isoformat() if r.get("ingestao_ts") else None,
                r.get("payload_json"),
                r.get("documento_json"),
                ts_export,
            )
            for r in rows
        ]

        # format(table=tabela): interpolação segura após validação do nome.
        sql = _MERGE.format(table=tabela)
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, params)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            cursor.close()
            raise
        finally:
            cursor.close()

        self._registrar_log(colecao, tabela, exportado_em, len(rows), len(rows))
        logger.info("Bronze upsert: tabela=%s documentos=%d", tabela, len(rows))
        return len(rows)

    def _registrar_log(self, colecao: str, tabela: str, exportado_em: datetime, documentos: int, inseridos: int) -> None:
        """Registra a exportação na tabela ExportacoesLog para auditoria.

        Falhas no log não propagam exceção — o dado já foi inserido com sucesso;
        perder o log é aceitável, perder o rollback do dado não é.
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(_LOG_INSERT, colecao, tabela, exportado_em.isoformat(), documentos, inseridos)
            self.connection.commit()
        except Exception:
            # Log falhou: registra no logger mas não relança — dado já foi salvo.
            logger.warning("Falha ao registrar log bronze para coleção %s", colecao)
            self.connection.rollback()
        finally:
            cursor.close()
