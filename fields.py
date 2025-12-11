import os
import requests
import mysql.connector
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
url = f"{BASE_URL}/dealFields"
params = {"api_token": API_KEY}

# ===============================
# REQUISIÇÃO
# ===============================
r = requests.get(url, params=params, timeout=30)
response = r.json()

if not response.get("success"):
    print("Erro na API do Pipedrive")
    exit()

data = response.get("data", [])

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
# CRIA TABELA
# ===============================

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

# ===============================
# MONTAGEM DOS DADOS
# ===============================

valores = []
sem_id = 0

for f in data:
    field_id = f.get("id")
    field_key = f.get("key")

    # Se não tiver id, usa hash da key
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
        f.get("edit_flag")   # indica se é customizado
    ))

# ===============================
# UPSERT
# ===============================

sql = """
INSERT INTO tb_fields_deals (
    id,
    field_key,
    name,
    field_type,
    entity_type,
    is_mandatory,
    is_custom
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    field_key   = VALUES(field_key),
    name        = VALUES(name),
    field_type  = VALUES(field_type),
    entity_type = VALUES(entity_type),
    is_mandatory= VALUES(is_mandatory),
    is_custom   = VALUES(is_custom);
"""

cursor.executemany(sql, valores)
conn.commit()

print(f"\n{cursor.rowcount} fields inseridos/atualizados em tb_fields")

cursor.close()
conn.close()