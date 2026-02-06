FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Build args - Mantendo MySQL e Adicionando PostgreSQL
ARG PIPEDRIVE_API_KEY
ARG PIPEDRIVE_BASE_URL
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_DATABASE
ARG DB_USER
ARG DB_PASSWORD
ARG DB_DATABASE
ARG TIMEZONE

# Dependências do sistema (Adicionado libpq-dev e gcc para o Postgres)
RUN apt-get update && apt-get install -y \
    cron \
    procps \
    tzdata \
    nano \
    netcat-openbsd \
    gettext-base \
    dos2unix \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia dependências e código-fonte
COPY requirements.txt /app/
COPY src /app/src
COPY wait-for-it.sh /app/wait-for-it.sh
COPY .env /app/.env

# Permissões do wait-for-it
RUN chmod +x /app/wait-for-it.sh

# Instala dependências Python (O requirements.txt deve conter as duas libs agora)
RUN pip install --no-cache-dir -r requirements.txt

# Diretório de logs
RUN mkdir -p /app/logs && touch /app/logs/cron.log

# Copia crontab original
COPY crontab /etc/cron.d/pipedrive_cron

RUN chmod 0644 /etc/cron.d/pipedrive_cron \
    && chown root:root /etc/cron.d/pipedrive_cron \
    && dos2unix /etc/cron.d/pipedrive_cron

# Inicia cron no foreground
CMD ["cron", "-f"]