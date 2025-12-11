FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    cron \
    procps \
    tzdata \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia e instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicação (scripts Python) e o wrapper
COPY . /app
COPY start.sh /usr/local/bin/start.sh

# Permissões para o script de inicialização
RUN chmod +x /usr/local/bin/start.sh

# Cria diretório para logs e log file
RUN mkdir -p /app/logs
RUN touch /app/logs/cron.log

# Cron a cada 1 hora, seg-sex, 9h às 16h
# NOTA: O script start.sh garante que as variáveis do .env estarão no ambiente
RUN echo "0 9-16 * * 1-5 cd /app && \
/usr/local/bin/python deals.py && \
/usr/local/bin/python fields.py && \
/usr/local/bin/python pipelines.py && \
/usr/local/bin/python stages.py && \
/usr/local/bin/python users.py \
>> /app/logs/cron.log 2>&1" > /etc/cron.d/pipedrive_cron

# Permissões
RUN chmod 0644 /etc/cron.d/pipedrive_cron

# Inicia o script wrapper, que exporta o ambiente e executa o cron -f
CMD ["/usr/local/bin/start.sh"]