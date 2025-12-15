Executar
# Apaga container caso já exista
docker-compose down

# Construção da imagem
docker-compose build --no-cache

# Criação do container
docker-compose -p pipedrive up -d

# Construção e criação
docker-compose build --no-cache && docker-compose -p pipedrive up -d

# Testar manualmente o deals.py (AJUSTADO)
docker exec -it pipedrive_cron bash
python3 src/deals.py

# Execução para todas as tabelas (AJUSTADO)
docker exec -it pipedrive_cron bash
python3 src/stages.py && python3 src/fields.py && python3 src/pipelines.py && python3 src/users.py && python3 src/deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it pipedrive_cron bash
ls -l /etc/cron.d/pipedrive_cron
cat /etc/cron.d/pipedrive_cron

# Reconstruir apenas a imagem do serviço cron
docker-compose -p pipedrive build cron

# Recriar apenas o container cron (Manutenção dos scripts)
docker-compose -p pipedrive up -d --no-deps --force-recreate cron