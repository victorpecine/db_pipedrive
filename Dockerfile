FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Build args (serão injetados no envsubst)
ARG PIPEDRIVE_API_KEY
ARG PIPEDRIVE_BASE_URL
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_DATABASE
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
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia dependências e código-fonte
COPY requirements.txt /app/
COPY . /app

# Permissões do wait-for-it
RUN chmod +x /app/wait-for-it.sh

# Instala dependências Python
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
