FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Build args
ARG PIPEDRIVE_API_KEY
ARG PIPEDRIVE_BASE_URL
ARG DB_USER
ARG DB_PASSWORD
ARG DB_DATABASE
ARG TIMEZONE

# Dependências do sistema
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

WORKDIR /app

COPY requirements.txt /app/
COPY src /app/src
COPY wait-for-it.sh /app/wait-for-it.sh
COPY .env /app/.env

RUN chmod +x /app/wait-for-it.sh

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs && touch /app/logs/cron.log

# Copia crontab
COPY crontab /etc/cron.d/pipedrive_postgre_cron

RUN dos2unix /app/wait-for-it.sh /etc/cron.d/pipedrive_postgre_cron \
    && chmod 0644 /etc/cron.d/pipedrive_postgre_cron \
    && chown root:root /etc/cron.d/pipedrive_postgre_cron \
    && crontab /etc/cron.d/pipedrive_postgre_cron

CMD ["cron", "-f"]