import requests
import pandas as pd
import mysql.connector
from   datetime import datetime
from   zoneinfo import ZoneInfo


API_KEY = "4436c240ab88d75dae896315502cab8d36defeae"
BASE_URL = "https://preambulotech2.pipedrive.com/api/v1"
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
print(f"\nTotal de deals no DataFrame: {len(df)}")

# print("\nCOLUNAS DISPONÍVEIS NO PIPEDRIVE:")
# print(df.columns.to_list())

df = df[[
    "id",
    "title",
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
df = df.rename(columns={
    "user_id.id": "user_id",
    "user_id.name": "user_name",
    "person_id.name": "person_name",
    "org_id.name": "org_name"
})

# Troca NaN por None (para virar NULL no MySQL)
df = df.where(pd.notnull(df), None)

# ===============================
# CONEXÃO MYSQL
# ===============================

conn = mysql.connector.connect(
    host="mysql",
    # port=3310,
    user="root",
    password="admin",
    database="db_pipedrive"
)

cursor = conn.cursor()

# ===============================
# CRIA TABELA (se não existir)
# ===============================

cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_deals (
    id              BIGINT NOT NULL,
    title           VARCHAR(255),
    value           DECIMAL(15,2),
    currency        VARCHAR(10),
    status          VARCHAR(50),
    pipeline_id     BIGINT,
    stage_id        BIGINT,
    user_id         BIGINT,
    user_name       VARCHAR(255),
    person_name     VARCHAR(255),
    org_name        VARCHAR(255),
    add_time        DATETIME,
    update_time     DATETIME,
    close_time      DATETIME,
    won_time        DATETIME,
    lost_time       DATETIME,
    PRIMARY KEY (id)
);
""")


# ===============================
# UPSERT
# ===============================
print("\nEnviando dados para o MySQL...")

sql = """
INSERT INTO tb_deals (
    id, title, value, currency, status,
    pipeline_id, stage_id,
    user_id, user_name,
    person_name, org_name,
    add_time, update_time, close_time, won_time, lost_time
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

ON DUPLICATE KEY UPDATE
    title       = VALUES(title),
    value       = VALUES(value),
    currency    = VALUES(currency),
    status      = VALUES(status),
    pipeline_id = VALUES(pipeline_id),
    stage_id    = VALUES(stage_id),
    user_id     = VALUES(user_id),
    user_name   = VALUES(user_name),
    person_name = VALUES(person_name),
    org_name    = VALUES(org_name),
    update_time = VALUES(update_time),
    close_time  = VALUES(close_time),
    won_time    = VALUES(won_time),
    lost_time   = VALUES(lost_time);
"""

dados = [tuple(x) for x in df.to_numpy()]
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
