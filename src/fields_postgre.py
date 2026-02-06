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
url = f"{BASE_URL}/dealFields"
params = {"api_token": API_KEY}

print("\nIniciando coleta de Deal Fields do Pipedrive...")
try:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    response = r.json()

    if not response.get("success"):
        print("Erro na API do Pipedrive")
        exit()

    data = response.get("data", [])
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

    # Criação da Tabela (Sintaxe Postgres)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_fields_deals (
        id BIGINT PRIMARY KEY,
        field_key VARCHAR(255),
        name VARCHAR(255),
        field_type VARCHAR(100),
        entity_type VARCHAR(50),
        is_mandatory BOOLEAN,
        is_custom BOOLEAN
    );
    """)

    # Preparação dos dados
    valores = []
    sem_id = 0

    for f in data:
        field_id = f.get("id")
        field_key = f.get("key")

        # Fallback para IDs ausentes
        if field_id is None and field_key:
            field_id = abs(hash(field_key)) % (10**12)

        if field_id is None:
            sem_id += 1
            continue

        valores.append((
            field_id,
            field_key,
            f.get("name"),
            f.get("field_type"),
            f.get("entity_type"),
            f.get("is_mandatory"),
            f.get("edit_flag")  # indica se é customizado
        ))

    # SQL de UPSERT (Sintaxe ON CONFLICT do Postgres)
    sql_upsert = """
    INSERT INTO tb_fields_deals (
        id, field_key, name, field_type, entity_type, is_mandatory, is_custom
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        field_key   = EXCLUDED.field_key,
        name        = EXCLUDED.name,
        field_type  = EXCLUDED.field_type,
        entity_type = EXCLUDED.entity_type,
        is_mandatory= EXCLUDED.is_mandatory,
        is_custom   = EXCLUDED.is_custom;
    """

    # Execução em lote para melhor performance
    extras.execute_batch(cursor, sql_upsert, valores)
    
    conn.commit()
    print(f"{len(valores)} fields sincronizados com sucesso no PostgreSQL.")

except Exception as err:
    print(f"Erro de Banco de Dados: {err}")
    if 'conn' in locals(): conn.rollback()

finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()