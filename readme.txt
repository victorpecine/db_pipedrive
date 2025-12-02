Executar
# Apaga container caso já exista
docker-compose down

# Construção da imagem
docker-compose build --no-cache

# Criação do container
docker-compose -p pipedrive up -d

# Construção e criação
docker-compose build --no-cache && docker-compose -p pipedrive up -d

# Testar manualmente o deals.py
docker exec -it pipedrive_cron bash
cd /app
python3 deals.py

# Execução para todas as tabelas
python3 stages.py && python3 fields.py && python3 pipelines.py && python3 users.py && python3 deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it pipedrive_cron bash
ls -l /etc/cron.d/pipedrive_cron
cat /etc/cron.d/pipedrive_cron