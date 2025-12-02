import requests
import mysql.connector


API_KEY = "4436c240ab88d75dae896315502cab8d36defeae"
BASE_URL = "https://preambulotech2.pipedrive.com/api/v1"

url = f"{BASE_URL}/users"
params = {"api_token": API_KEY}

r = requests.get(url, params=params)
data = r.json().get("data", [])

conn = mysql.connector.connect(
    host="mysql",
    # port=3310,
    user="root",
    password="admin",
    database="db_pipedrive"
)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tb_users (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255)
);
""")

sql = """
INSERT INTO tb_users (id, name)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
    name = VALUES(name);
"""

valores = [(u["id"], u["name"]) for u in data]

cursor.executemany(sql, valores)
conn.commit()

print(f"\n{cursor.rowcount} users inseridos/atualizados em tb_users")

cursor.close()
conn.close()
