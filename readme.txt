# Parar o container
docker-compose pipedrive down

# Construção e criação
docker-compose -p pipedrive build --no-cache && docker-compose -p pipedrive up -d

# Testar manualmente o deals.py
docker exec -it pipedrive_cron bash
python3 src/deals.py

# Execução para todas as tabelas
docker exec -it pipedrive_cron bash
python3 src/stages.py && python3 src/fields.py && python3 src/pipelines.py && python3 src/users.py && python3 src/deals.py

# Ver se o cron consegue ler o arquivo
docker exec -it pipedrive_cron bash
ls -l /etc/cron.d/pipedrive_cron
cat /etc/cron.d/pipedrive_cron

# Reconstruir apenas a imagem do serviço cron
docker-compose -p pipedrive build cron

# Recriar apenas o container cron
docker-compose -p pipedrive up -d --no-deps --force-recreate cron

# Teste cron no bash docker
    1. Entrar no container
    docker exec -it pipedrive_cron bash

    2. Listar arquivos de cron instalados
    ls -l /etc/cron.d/

    3. Exibir o conteúdo do seu arquivo de cron
    cat /etc/cron.d/pipedrive_cron

    4. Ver se o cron carregou algum job
    crontab -l

    5. Verificar se o processo cron está rodando
    ps aux | grep cron

    6. Verificar CRLF

    7. Ver logs cron
    cat logs/cron.log