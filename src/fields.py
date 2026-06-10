"""
fields.py
---------
Sincroniza os Deal Fields do Pipedrive com a tabela `tb_fields_deals`
no PostgreSQL.

Estratégia de chave primária
-----------------------------
O `field_key` é o identificador canônico e estável de cada campo na
API do Pipedrive (ex.: "abc123_custom_field"). Ele é usado como PK
em vez do `id` numérico porque:
  - O `id` numérico pode não existir em campos de sistema;
  - O `id` numérico pode divergir entre ambientes (sandbox vs produção);
  - O `field_key` é a referência usada pelo Pipedrive nas respostas de deals.

O `pipedrive_id` é armazenado apenas como referência, podendo ser NULL.

DDL esperado
------------
    CREATE TABLE IF NOT EXISTS tb_fields_deals (
        field_key    VARCHAR(255) PRIMARY KEY,
        pipedrive_id BIGINT,
        name         VARCHAR(255),
        field_type   VARCHAR(100),
        entity_type  VARCHAR(50),
        is_mandatory BOOLEAN,
        is_custom    BOOLEAN
    );

Variáveis de ambiente necessárias (.env)
-----------------------------------------
    PIPEDRIVE_API_KEY
    PIPEDRIVE_BASE_URL
    DB_HOST       (padrão: "postgres")
    DB_USER       (padrão: "postgres")
    DB_PASSWORD
    DB_DATABASE
    DB_PORT       (padrão: "5432")
"""

import logging
import os

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2 import extras

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Credenciais Pipedrive
API_KEY  = os.environ["PIPEDRIVE_API_KEY"]
BASE_URL = os.environ["PIPEDRIVE_BASE_URL"]

# Credenciais PostgreSQL
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")
DB_PORT     = os.environ.get("DB_PORT", "5432")


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------

def fetch_deal_fields() -> list[dict]:
    """
    Consulta o endpoint /dealFields da API do Pipedrive.

    Returns
    -------
    list[dict]
        Lista de objetos de campo retornados pela API.

    Raises
    ------
    requests.HTTPError
        Se a API retornar status HTTP de erro (4xx / 5xx).
    ValueError
        Se o corpo da resposta indicar falha no campo `success`.
    """
    url    = f"{BASE_URL}/dealFields"
    params = {"api_token": API_KEY}

    logger.info("Consultando Pipedrive: %s", url)

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    body = response.json()

    if not body.get("success"):
        raise ValueError(f"Pipedrive retornou success=false: {body}")

    fields = body.get("data", [])
    logger.info("%d fields recebidos da API.", len(fields))

    return fields


# ---------------------------------------------------------------------------
# Transformação
# ---------------------------------------------------------------------------

def transform(fields: list[dict]) -> tuple[list[tuple], list[dict]]:
    """
    Converte a lista bruta de fields em tuplas prontas para o UPSERT.

    Campos sem `field_key` são descartados e registrados separadamente,
    pois não possuem identificador canônico para garantir idempotência.

    Parameters
    ----------
    fields : list[dict]
        Dados brutos retornados por `fetch_deal_fields`.

    Returns
    -------
    rows : list[tuple]
        Tuplas no formato (field_key, pipedrive_id, name, field_type,
        entity_type, is_mandatory, is_custom).
    skipped : list[dict]
        Registros ignorados por ausência de `field_key`.
    """
    rows    = []
    skipped = []

    for field in fields:
        field_key = field.get("key")

        if not field_key:
            # Sem field_key não há como garantir idempotência — descarta.
            skipped.append(field)
            continue

        rows.append((
            field_key,              # PK — identificador canônico e estável
            field.get("id"),        # pipedrive_id — referência, pode ser NULL
            field.get("name"),
            field.get("field_type"),
            field.get("entity_type"),
            field.get("is_mandatory"),
            field.get("edit_flag"),  # True indica campo customizado
        ))

    return rows, skipped


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

SQL_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS tb_fields_deals (
        field_key    VARCHAR(255) PRIMARY KEY,
        pipedrive_id BIGINT,
        name         VARCHAR(255),
        field_type   VARCHAR(100),
        entity_type  VARCHAR(50),
        is_mandatory BOOLEAN,
        is_custom    BOOLEAN
    );
"""

SQL_UPSERT = """
    INSERT INTO tb_fields_deals (
        field_key, pipedrive_id, name, field_type,
        entity_type, is_mandatory, is_custom
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (field_key) DO UPDATE SET
        pipedrive_id = EXCLUDED.pipedrive_id,
        name         = EXCLUDED.name,
        field_type   = EXCLUDED.field_type,
        entity_type  = EXCLUDED.entity_type,
        is_mandatory = EXCLUDED.is_mandatory,
        is_custom    = EXCLUDED.is_custom;
"""


def upsert(conn: psycopg2.extensions.connection, rows: list[tuple]) -> int:
    """
    Garante a existência da tabela e executa o UPSERT em lote.

    O `ON CONFLICT (field_key)` torna a operação idempotente: executar
    o script múltiplas vezes não gera duplicatas.

    Parameters
    ----------
    conn : psycopg2.extensions.connection
        Conexão ativa com o PostgreSQL.
    rows : list[tuple]
        Tuplas preparadas por `transform`.

    Returns
    -------
    int
        Quantidade de linhas processadas.

    Raises
    ------
    psycopg2.Error
        Qualquer erro de banco propagado para o chamador fazer rollback.
    """
    with conn.cursor() as cursor:
        cursor.execute(SQL_CREATE_TABLE)
        extras.execute_batch(cursor, SQL_UPSERT, rows)

    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    """Orquestra extração, transformação e carga."""

    # 1. Extração
    raw_fields = fetch_deal_fields()

    # 2. Transformação
    rows, skipped = transform(raw_fields)

    if skipped:
        logger.warning(
            "%d field(s) ignorado(s) por ausência de field_key: %s",
            len(skipped),
            skipped,
        )

    if not rows:
        logger.warning("Nenhum field válido para sincronizar.")
        return

    # 3. Carga
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE,
        port=DB_PORT,
    )

    try:
        total = upsert(conn, rows)
        logger.info("%d field(s) sincronizado(s) com sucesso.", total)

    except psycopg2.Error as err:
        conn.rollback()
        logger.exception("Erro no banco de dados — rollback executado: %s", err)
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()