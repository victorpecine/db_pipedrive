import os
import requests
import mysql.connector
from   dotenv import load_dotenv


# Carrega as variáveis de ambiente do arquivo .env no diretório atual
load_dotenv()

API_KEY  = os.environ.get("PIPEDRIVE_API_KEY")
BASE_URL = os.environ.get("PIPEDRIVE_BASE_URL")

# Dados de Conexão MySQL
DB_HOST     = os.environ.get("MYSQL_HOST", "localhost")
DB_PORT     = int(os.environ.get("MYSQL_PORT", 3310))
DB_USER     = os.environ.get("MYSQL_USER")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD")
DB_DATABASE = os.environ.get("MYSQL_DATABASE")

# Fuso Horário
TIMEZONE_NAME = os.environ.get("TIMEZONE", "America/Sao_Paulo")

# ===============================
# EXTRAÇÃO DE DADOS DO PIPEDRIVE
# ===============================
# Variáveis de Configuração de URL e Parâmetros
url = f"{BASE_URL}/stages"
params = {"api_token": API_KEY}

r = requests.get(url, params=params)
data = r.json().get("data", [])

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        # host="localhost",  # Para teste local
        # port=3310,  # Para teste local
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE 
    )

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tb_stages (
        id BIGINT PRIMARY KEY,
        pipeline_id BIGINT,
        name VARCHAR(255)
    );
    """)

    sql = """
    INSERT INTO tb_stages (id, pipeline_id, name)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        pipeline_id = VALUES(pipeline_id);
    """

    valores = [(s["id"], s["pipeline_id"], s["name"]) for s in data]

    cursor.executemany(sql, valores)
    conn.commit()

    print(f"\n{cursor.rowcount} stages inseridos/atualizados em tb_stages")

except mysql.connector.Error as err:
    print(f"Erro de Banco de Dados: {err}")

finally:
    cursor.close()
    conn.close()