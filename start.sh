#!/bin/bash

# Este script garante que o cron terá acesso a TODAS as variáveis
# injetadas pelo docker-compose (PIPEDRIVE_*, MYSQL_*, etc.)

# 1. Lista todas as variáveis de ambiente atuais
env > /etc/environment

# 2. Inicia o daemon do cron em foreground
cron -f