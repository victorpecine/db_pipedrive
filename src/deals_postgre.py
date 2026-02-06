import os
import requests
import pandas as pd
import psycopg2
from psycopg2 import extras
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

API_KEY  = os.environ.get("PIPEDRIVE_API_KEY")
BASE_URL = os.environ.get("PIPEDRIVE_BASE_URL")

# Dados de Conexão PostgreSQL (Lendo as novas variáveis)
DB_HOST     = os.environ.get("DB_HOST", "postgres")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_DATABASE = os.environ.get("DB_DATABASE")
DB_PORT     = os.environ.get("DB_PORT", "5432")

# Fuso Horário
TIMEZONE_NAME = os.environ.get("TIMEZONE", "America/Sao_Paulo")

# ===============================
# EXTRAÇÃO DE DADOS DO PIPEDRIVE
# ===============================
url = f"{BASE_URL}/deals"

params = {
    "api_token": API_KEY,
    "limit": 500,
    "start": 0
}

todos_deals = []
pagina = 1

print("\nIniciando coleta de deals do Pipedrive...")
while True:
    response = requests.get(url, params=params, timeout=20)

    if response.status_code != 200:
        print("Erro HTTP:", response.status_code, response.text)
        break

    data = response.json()

    if not data.get("success"):
        print("Erro retornado pela API")
        break

    deals = data.get("data")

    if not deals:
        break

    todos_deals.extend(deals)
    print(f"Página {pagina} - {len(deals)} deals (total: {len(todos_deals)})")

    pag = data["additional_data"]["pagination"]
    if not pag["more_items_in_collection"]:
        break

    params["start"] = pag["next_start"]
    pagina += 1

    if pagina > 1000:
        print("Loop interrompido por segurança")
        break

# ===============================
# TRATAMENTO COM PANDAS
# ===============================
df = pd.json_normalize(todos_deals)

# Seleção das colunas necessárias
df = df[[
    "id",
    "title",
    "6564ef40269f2f1d4d0783d8b73b79773e13b158",
    "value",
    "currency",
    "status",
    "pipeline_id",
    "stage_id",
    "user_id.id",
    "user_id.name",
    "person_id.name",
    "org_id.name",
    "add_time",
    "update_time",
    "2ad149d52679d84b85414d1d322c832fd053602c",
    "close_time",
    "won_time",
    "lost_time"
]]

# Renomear colunas
df = df.rename(
    columns={
        "user_id.id": "id_responsavel",
        "user_id.name": "nome_responsavel",
        "person_id.name": "nome_cliente",
        "org_id.name": "nome_empresa",
        "6564ef40269f2f1d4d0783d8b73b79773e13b158": "cod_cliente",
        "2ad149d52679d84b85414d1d322c832fd053602c": "data_primeira_atividade"
})

# Conversão de timezone
colunas_data = ['add_time', 'update_time', 'close_time', 'won_time', 'lost_time']

for col in colunas_data:
    if col in df.columns:
        df[col] = (
            pd.to_datetime(df[col], errors='coerce', utc=True)
              .dt.tz_convert(TIMEZONE_NAME)
              .dt.tz_localize(None)
        )

# Tratamento de nulos
df = df.where(pd.notnull(df), None)

# Ordem das colunas para o SQL
colunas_sql_order = [
    "id", "title", "cod_cliente", "value",
    "currency", "status", "pipeline_id", "stage_id",
    "id_responsavel", "nome_responsavel",
    "nome_cliente", "nome_empresa", 
    "add_time", "update_time", "close_time", 
    "data_primeira_atividade",
    "won_time", "lost_time"
]

df_ordenado = df[colunas_sql_order]
ids_api = set(df_ordenado["id"].tolist())

# Preparação dos dados para o banco
dados = []
for index, row in df_ordenado.iterrows():
    tupla = []
    for col in colunas_sql_order:
        valor = row[col]
        if pd.isna(valor):
            tupla.append(None)
        else:
            tupla.append(valor)
    dados.append(tuple(tupla))

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
    CREATE TABLE IF NOT EXISTS tb_deals (
        id                      BIGINT NOT NULL,
        title                   VARCHAR(255),
        cod_cliente             VARCHAR(255),
        value                   DECIMAL(15,2),
        currency                VARCHAR(10),
        status                  VARCHAR(50),
        pipeline_id             BIGINT,
        stage_id                BIGINT,
        id_responsavel          BIGINT,
        nome_responsavel        VARCHAR(255),
        nome_cliente            VARCHAR(255),
        nome_empresa            VARCHAR(255),
        add_time                TIMESTAMP,
        update_time             TIMESTAMP,
        close_time              TIMESTAMP,
        data_primeira_atividade TIMESTAMP,
        won_time                TIMESTAMP,
        lost_time               TIMESTAMP,
        deal_deleted            SMALLINT NOT NULL DEFAULT 0,
        PRIMARY KEY (id)
    );
    """)

    # SQL Upsert (Sintaxe ON CONFLICT do Postgres)
    sql_upsert = """
    INSERT INTO tb_deals (
        id, title, cod_cliente, value, currency, status,
        pipeline_id, stage_id, id_responsavel, nome_responsavel,
        nome_cliente, nome_empresa, add_time, update_time,
        close_time, data_primeira_atividade, won_time, lost_time, deal_deleted
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
    ON CONFLICT (id) DO UPDATE SET
        title                   = EXCLUDED.title,
        value                   = EXCLUDED.value,
        cod_cliente             = EXCLUDED.cod_cliente,
        currency                = EXCLUDED.currency,
        status                  = EXCLUDED.status,
        pipeline_id             = EXCLUDED.pipeline_id,
        stage_id                = EXCLUDED.stage_id,
        id_responsavel          = EXCLUDED.id_responsavel,
        nome_responsavel        = EXCLUDED.nome_responsavel,
        nome_cliente            = EXCLUDED.nome_cliente,
        nome_empresa            = EXCLUDED.nome_empresa,
        add_time                = EXCLUDED.add_time,
        update_time             = EXCLUDED.update_time,
        close_time              = EXCLUDED.close_time,
        data_primeira_atividade = EXCLUDED.data_primeira_atividade,
        won_time                = EXCLUDED.won_time,
        lost_time               = EXCLUDED.lost_time,
        deal_deleted            = 0;
    """

    # Execução do Upsert
    extras.execute_batch(cursor, sql_upsert, dados)

    # Identificação de deals deletados no Pipedrive
    cursor.execute("SELECT id FROM tb_deals")
    ids_banco = {row[0] for row in cursor.fetchall()}
    ids_excluidos = ids_banco - ids_api

    if ids_excluidos:
        extras.execute_batch(
            cursor, 
            "UPDATE tb_deals SET deal_deleted = 1 WHERE id = %s", 
            [(i,) for i in ids_excluidos]
        )

    # Registro de log de execução
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atualizacoes (
            id SERIAL PRIMARY KEY,
            data_atualizacao TIMESTAMP NOT NULL,
            total_deals INT NOT NULL
        )
    """)
    
    timestamp_log = datetime.now(ZoneInfo(TIMEZONE_NAME))
    cursor.execute(
        "INSERT INTO atualizacoes (data_atualizacao, total_deals) VALUES (%s, %s)",
        (timestamp_log, len(ids_api))
    )

    conn.commit()
    print(f"\n{len(ids_api)} deals processados com sucesso no PostgreSQL.")

except Exception as err:
    print(f"Erro no processamento: {err}")
    if 'conn' in locals(): conn.rollback()
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conn' in locals(): conn.close()