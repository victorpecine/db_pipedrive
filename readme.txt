# Parar o container
docker-compose -p pipedrive_mysql down

# Parar e remover volumes (reset completo)
docker-compose -p pipedrive_mysql down -v

# Construção e criação
docker-compose -p pipedrive_mysql build --no-cache && docker-compose -p pipedrive_mysql up -d

# Testar manualmente o deals.py
docker exec -it mysql_cron bash
python3 src/deals.py

# Execução para todas as tabelas
docker exec -it mysql_cron bash
python3 src/stages.py && python3 src/fields.py && python3 src/pipelines.py && python3 src/users.py && python3 src/deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it mysql_cron bash
ls -l /etc/cron.d/mysql_cron
cat /etc/cron.d/mysql_cron

# Reconstruir apenas a imagem do serviço cron
docker-compose -p pipedrive_mysql build cron

# Recriar apenas o container cron
docker-compose -p pipedrive_mysql up -d --no-deps --force-recreate cron

# Teste cron no bash docker

1. Entrar no container
docker exec -it mysql_cron bash

2. Listar arquivos de cron instalados
ls -l /etc/cron.d/

3. Exibir o conteúdo do seu arquivo de cron
cat /etc/cron.d/mysql_cron

4. Ver se o cron carregou algum job
crontab -l
# OBS: Pode retornar "no crontab for root" pois usamos /etc/cron.d/

5. Verificar se o processo cron está rodando
ps aux | grep cron
# Deve aparecer: cron -f

6. Verificar CRLF (se suspeitar de problema de formatação)
cat -A /etc/cron.d/mysql_cron
# Não deve aparecer ^M no final das linhas

7. Ver logs do cron
cat /app/logs/cron.log

# Testar conexão manual com MySQL
/app/wait-for-it.sh mysql:3306 -t 60
