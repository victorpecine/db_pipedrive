Executar
# Apaga container caso já exista
docker-compose down

# Construção da imagem
docker-compose build --no-cache

# Criação do container
docker-compose -p pipedrive up -d

docker-compose build --no-cache && docker-compose -p pipedrive up -d

# Testar manualmente o deals.py
docker exec -it pipedrive_cron bash
cd /app
python3 deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it pipedrive_cron bash
ls -l /etc/cron.d/pipedrive_cron
cat /etc/cron.d/pipedrive_cron