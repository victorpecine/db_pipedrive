import os
import requests
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

API_KEY  = os.environ.get("PIPEDRIVE_API_KEY")
BASE_URL = os.environ.get("PIPEDRIVE_BASE_URL")

# Dados de Conexão PostgreSQL
DB_HOST     = os.environ.get("DB_HOST", "postgres")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")
DB_PORT     = os.environ.get("DB_PORT", "5432")

# ===============================
# EXTRAÇÃO DE DADOS DO PIPEDRIVE
# ===============================
url = f"{BASE_URL}/stages"
params = {"api_token": API_KEY}

try:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json().get("data") or []
except Exception as e:
    print(f"Erro na requisição: {e}")
    exit()

# ===============================
# PERSISTÊNCIA NO POSTGRESQL
# ===============================
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # Criação da tabela (Sintaxe Postgres)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_stages (
        id BIGINT PRIMARY KEY,
        pipeline_id BIGINT,
        name VARCHAR(255)
    );
    """)

    # SQL de UPSERT (Sintaxe ON CONFLICT do Postgres)
    sql = """
    INSERT INTO tb_stages (id, pipeline_id, name)
    VALUES (%s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        pipeline_id = EXCLUDED.pipeline_id;
    """

    # Montagem dos valores
    valores = [(s["id"], s["pipeline_id"], s["name"]) for s in data]

    # Execução em lote
    if valores:
        extras.execute_batch(cursor, sql, valores)
    
    conn.commit()
    print(f"\n{len(valores)} stages sincronizados com sucesso no PostgreSQL.")

except Exception as err:
    print(f"Erro de Banco de Dados: {err}")
    if 'conn' in locals(): conn.rollback()

finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()