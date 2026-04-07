#!/bin/bash
# Cria a base de dados 'litellm' para o LiteLLM (budget tracking)
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE litellm'
    WHERE NOT EXISTS (
        SELECT FROM pg_database WHERE datname = 'litellm'
    )\gexec
EOSQL

echo "Database 'litellm' ready."
