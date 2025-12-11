import os
import requests
import pandas as pd
import mysql.connector
from   datetime import datetime
from   zoneinfo import ZoneInfo
from   dotenv import load_dotenv


# Carrega as variáveis de ambiente do arquivo .env no diretório atual
load_dotenv()

API_KEY  = os.environ.get("PIPEDRIVE_API_KEY")
BASE_URL = os.environ.get("PIPEDRIVE_BASE_URL")

# Dados de Conexão MySQL
DB_HOST     = "mysql"
DB_USER     = os.environ.get("MYSQL_USER")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD")
DB_DATABASE = os.environ.get("MYSQL_DATABASE")

# Fuso Horário
TIMEZONE_NAME = os.environ.get("TIMEZONE", "America/Sao_Paulo")

# ===============================
# EXTRAÇÃO DE DADOS DO PIPEDRIVE
# ===============================
# Variáveis de Configuração de URL e Parâmetros
url = f"{BASE_URL}/deals"

params = {
    "api_token": API_KEY, # Usando a chave lida do ambiente
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
    print(f"\nPágina {pagina} - {len(deals)} deals (total: {len(todos_deals)})")


    pag = data["additional_data"]["pagination"]
    if not pag["more_items_in_collection"]:
        break

    params["start"] = pag["next_start"]
    pagina += 1

    # Proteção contra loop infinito
    if pagina > 1000:
        print("Loop interrompido por segurança")
        break
    
# ===============================
# DATAFRAME
# ===============================

df = pd.json_normalize(todos_deals)

df = df[[
    "id",
    "title",
    "6564ef40269f2f1d4d0783d8b73b79773e13b158",  # Campo personalizado "Código do Cliente"
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
    "close_time",
    "won_time",
    "lost_time"
]]

# Renomear colunas para MySQL
df = df.rename(
    columns={
        "user_id.id": "id_responsavel",
        "user_id.name": "nome_responsavel",
        "person_id.name": "nome_cliente",
        "org_id.name": "nome_empresa",
        "6564ef40269f2f1d4d0783d8b73b79773e13b158": "cod_cliente"
})

# Troca NaN por None (para virar NULL no MySQL)
df = df.where(pd.notnull(df), None)

# ===============================
# CONEXÃO MYSQL
# ===============================

conn = mysql.connector.connect(
    host=DB_HOST,
    # host="localhost",  # Para teste local
    # port=3310,  # Para teste local
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_DATABASE 
)

cursor = conn.cursor()

# ===============================
# CRIA TABELA (se não existir)
# ===============================

cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_deals (
    id                BIGINT NOT NULL,
    title             VARCHAR(255),
    cod_cliente       VARCHAR(10),
    value             DECIMAL(15,2),
    currency          VARCHAR(10),
    status            VARCHAR(50),
    pipeline_id       BIGINT,
    stage_id          BIGINT,
    id_responsavel    BIGINT,
    nome_responsavel  VARCHAR(255),
    nome_cliente      VARCHAR(255),
    nome_empresa      VARCHAR(255),
    add_time          DATETIME,
    update_time       DATETIME,
    close_time        DATETIME,
    won_time          DATETIME,
    lost_time         DATETIME,
    PRIMARY KEY (id)
);
""")

# ===============================
# UPSERT
# ===============================

sql = """
INSERT INTO tb_deals (
    id, title,
    cod_cliente, value,
    currency, status,
    pipeline_id, stage_id,
    id_responsavel, nome_responsavel,
    nome_cliente,
    nome_empresa, add_time,
    update_time, close_time,
    won_time, lost_time
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

ON DUPLICATE KEY UPDATE
    title               = VALUES(title),
    value               = VALUES(value),
    cod_cliente         = VALUES(cod_cliente),
    currency            = VALUES(currency),
    status              = VALUES(status),
    pipeline_id         = VALUES(pipeline_id),
    stage_id            = VALUES(stage_id),
    id_responsavel      = VALUES(id_responsavel),
    nome_responsavel    = VALUES(nome_responsavel),
    nome_cliente        = VALUES(nome_cliente),
    nome_empresa        = VALUES(nome_empresa),
    add_time            = VALUES(add_time),
    update_time         = VALUES(update_time),
    close_time          = VALUES(close_time),
    won_time            = VALUES(won_time),
    lost_time           = VALUES(lost_time);
"""

# Define a ordem exata das 17 colunas para garantir o alinhamento 
# com a query SQL abaixo (UPSERT).
colunas_sql_order = [
    "id", "title", "cod_cliente", "value",
    "currency", "status", "pipeline_id", "stage_id",
    "id_responsavel", "nome_responsavel",
    "nome_cliente", "nome_empresa", 
    "add_time", "update_time",
    "close_time", "won_time", "lost_time"
]

df_ordenado = df[colunas_sql_order]
dados = [tuple(x) for x in df_ordenado.to_numpy()] # Formato exigido (lista de tuplas) para execução em lote via executemany
cursor.executemany(sql, dados)
total_deals = cursor.rowcount

# Cria tabela para conter timestamp da atualização
cursor.execute("""
    CREATE TABLE IF NOT EXISTS atualizacoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        data_atualizacao DATETIME NOT NULL,
        total_deals INT NOT NULL
    )
    """)
timestamp = datetime.now(ZoneInfo("America/Sao_Paulo"))
cursor.execute(
    "INSERT INTO atualizacoes (data_atualizacao, total_deals) VALUES (%s, %s)", (timestamp, total_deals)
    )

conn.commit()

print(f"\n{total_deals} deals inseridos/atualizados em tb_deals")

cursor.close()
conn.close()
