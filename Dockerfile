FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    cron \
    procps \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia arquivos necessários
COPY . /app

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Cria diretório para logs
RUN mkdir -p /app/logs

# Cron a cada 1 hora, seg-sex, 9h às 16h
RUN echo "0 9-16 * * 1-5 cd /app && \
/usr/local/bin/python deals.py && \
/usr/local/bin/python fields.py && \
/usr/local/bin/python pipelines.py && \
/usr/local/bin/python stages.py && \
/usr/local/bin/python users.py \
>> /app/logs/cron.log 2>&1" > /etc/cron.d/pipedrive_cron

# Permissões
RUN chmod 0644 /etc/cron.d/pipedrive_cron
RUN crontab /etc/cron.d/pipedrive_cron

# Cria log
RUN touch /app/logs/cron.log

# CMD ["/bin/sh", "-c", "cron && tail -f /app/logs/cron.log"]
CMD ["cron", "-f"]