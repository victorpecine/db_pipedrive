# Parar o container
docker-compose -p pipedrive_postgre down

# Parar e remover volumes (reset completo)
docker-compose -p pipedrive_postgre down -v

# Construção e criação
docker-compose -p pipedrive_postgre build --no-cache && docker-compose -p pipedrive_postgre up -d

# Testar manualmente o deals.py
docker exec -it postgre_cron bash
python3 src/deals.py

# Execução para todas as tabelas
docker exec -it postgre_cron bash
python3 src/stages.py && python3 src/fields.py && python3 src/pipelines.py && python3 src/users.py && python3 src/deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it postgre_cron bash
ls -l /etc/cron.d/postgre_cron
cat /etc/cron.d/postgre_cron

# Reconstruir apenas a imagem do serviço cron
docker-compose -p pipedrive_postgre build cron

# Recriar apenas o container cron
docker-compose -p pipedrive_postgre up -d --no-deps --force-recreate cron

# Teste cron no bash docker

1. Entrar no container
docker exec -it postgre_cron bash

2. Listar arquivos de cron instalados
ls -l /etc/cron.d/

3. Exibir o conteúdo do seu arquivo de cron
cat /etc/cron.d/postgre_cron

4. Ver se o cron carregou algum job
crontab -l
# OBS: Pode retornar "no crontab for root" pois usamos /etc/cron.d/

5. Verificar se o processo cron está rodando
ps aux | grep cron
# Deve aparecer: cron -f

6. Verificar CRLF (se suspeitar de problema de formatação)
cat -A /etc/cron.d/postgre_cron
# Não deve aparecer ^M no final das linhas

7. Ver logs do cron
cat /app/logs/deals.log
cat /app/logs/fields.log
cat /app/logs/pipelines.log
cat /app/logs/stages.log
cat /app/logs/users.log

# Testar conexão manual com PostgreSQL
/app/wait-for-it.sh postgre:5432 -t 60
