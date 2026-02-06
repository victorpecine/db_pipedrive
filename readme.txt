# Parar o container
docker-compose pipedrive down
docker-compose -f docker-compose-postgre.yml -p pipedrive_postgre down

# Construção e criação
docker-compose -p pipedrive build --no-cache && docker-compose -p pipedrive up -d
docker-compose -f docker-compose-postgre.yml -p pipedrive_postgre up -d --build

# Testar manualmente o deals.py
docker exec -it pipedrive_cron bash
python3 src/deals.py

# Execução para todas as tabelas
docker exec -it pipedrive_cron bash
python3 src/stages.py && python3 src/fields.py && python3 src/pipelines.py && python3 src/users.py && python3 src/deals.py
docker exec -it pipedrive_postgre_cron bash
python3 src/stages_postgre.py && python3 src/fields_postgre.py && python3 src/pipelines_postgre.py && python3 src/users_postgre.py && python3 src/deals_postgre.py

# Ver se o cron consegue ler o arquivo
docker exec -it pipedrive_cron bash
ls -l /etc/cron.d/pipedrive_cron
cat /etc/cron.d/pipedrive_cron

# Reconstruir apenas a imagem do serviço cron
docker-compose -p pipedrive build cron

# Recriar apenas o container cron
docker-compose -p pipedrive up -d --no-deps --force-recreate cron