import requests
import mysql.connector


API_KEY = "4436c240ab88d75dae896315502cab8d36defeae"
BASE_URL = "https://preambulotech2.pipedrive.com/api/v1"

url = f"{BASE_URL}/stages"
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

print(f"{cursor.rowcount} stages salvos")

cursor.close()
conn.close()
