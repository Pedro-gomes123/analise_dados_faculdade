"""Pipeline de Dimensões: aplica DDL e popula tabelas dim.* no SQL Server.

Por que tabelas de dimensão (dim.*)?
Na modelagem dimensional (Kimball), as tabelas de fato (gold.*) armazenam
os eventos/métricas — uma linha por medição. As dimensões armazenam os
atributos descritivos que enriquecem esses fatos:

Tabelas gerenciadas
-------------------
dim.Tempo
    Calendário de 2018 a 2030 gerado via CTE T-SQL.
    Atributos: dia da semana, semana ISO, mês, trimestre, estação do ano.
    Permite filtrar "todos os dados de Inverno" ou "finais de semana de 2024".

dim.Territorio
    Hierarquia geográfica de Recife (RPAs → bairros).
    Seed inicial das 6 RPAs; bairros adicionados externamente via GeoJSON.
    Permite agrupar dados por região administrativa da cidade.

dim.Indicador
    Catálogo de indicadores com limiares de alerta/crítico.
    Ex: temperatura_c alerta=35 critico=38, precipitacao_mm alerta=10 critico=30.
    O app usa esses limiares para colorir cards e ativar alertas visuais.

dim.Fonte
    Metadados operacionais de cada API (URL, frequência, licença, auth).
    Permite o app exibir "dados de" com link para a fonte original.
    Seed com as 6 fontes ativas do projeto.

Design
------
Todas as populações são idempotentes: usam INSERT ... WHERE NOT EXISTS
(implementado no DDL, não aqui). Este módulo apenas aplica o DDL e
registra o resultado no log. Re-executar não duplica dados de dimensão.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Path para o script DDL dim — calculado dinamicamente.
# parents[2]: dim_pipeline.py → pipelines/ → gold/ → projeto_5/ → sql/gold/
SQL_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "sql" / "gold" / "002_dim_tables.sql",
)


def _aplicar_ddl(connection, scripts=SQL_SCRIPTS) -> None:
    """Executa os scripts DDL das tabelas dimensão de forma idempotente.

    Divide cada arquivo .sql em batches pelo delimitador GO e faz commit
    por batch. O script 002_dim_tables.sql contém:
    - CREATE TABLE IF NOT EXISTS para dim.Tempo, Territorio, Indicador, Fonte.
    - INSERT via CTE recursiva para dim.Tempo (calendário 2018-2030).
    - INSERT WHERE NOT EXISTS para os seeds das demais dimensões.

    Por que o calendário é gerado via CTE T-SQL e não via Python?
    Uma CTE recursiva gera os 4.748 dias em uma única instrução SQL sem
    precisar construir uma lista em Python e iterar com executemany.
    É mais eficiente e não requer MAXRECURSION maior que 5000 (default=100).

    Args:
        connection: Conexão pyodbc ativa para o SQL Server.
        scripts: Iterable de paths dos arquivos .sql.

    Raises:
        Exception: Erro de banco; faz rollback e relança.
    """
    cursor = connection.cursor()
    try:
        for caminho in scripts:
            script = Path(caminho).read_text(encoding="utf-8")
            # re.split (?im): case-insensitive + multiline para o separador GO.
            for batch in re.split(r"(?im)^\s*GO\s*(?:--.*)?$", script):
                if batch.strip():
                    cursor.execute(batch)
                    connection.commit()
            logger.info("DDL dim aplicado: %s", Path(caminho).name)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def dim_pipeline(connection=None) -> None:
    """Aplica DDL e popula as tabelas dimensão.

    Abre e fecha a conexão automaticamente se `connection` não for fornecido.
    Pode ser re-executado a qualquer momento — idempotente por design.

    Por que dim_pipeline não recebe aplicar_ddl=bool como os outros pipelines?
    O dim_pipeline só faz DDL — toda a lógica de seed está no SQL.
    Se `aplicar_ddl=False` fosse suportado, o pipeline não faria nada.
    Manter a assinatura simples evita confusão.

    Args:
        connection: Conexão pyodbc pré-existente; se None, abre uma nova via
            `conectar_sql_server` e fecha no finally.
    """
    # Importação local: evita circular import com silver.database.
    from silver.database.sql_server import conectar_sql_server

    owns = connection is None
    if owns:
        connection = conectar_sql_server()

    try:
        # Todo o trabalho está no DDL — cria tabelas e insere seed data.
        _aplicar_ddl(connection)
        logger.info("Pipeline Dim concluído.")
    finally:
        # Fecha a conexão somente se foi aberta por este pipeline.
        if owns:
            connection.close()
