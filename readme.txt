Executar
-- Apaga container caso já exista
docker-compose down

- Construção da imagem
docker-compose build --no-cache

-- Criação do container
docker-compose -p pipedrive up -d