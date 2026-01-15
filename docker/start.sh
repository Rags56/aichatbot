#!/usr/bin/env bash
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-ai_chatbot}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-ai_chatbot123}"
POSTGRES_DB="${POSTGRES_DB:-ai_chatbot_db}"
MEILISEARCH_KEY="${MEILISEARCH_KEY:-masterKey123}"

export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB MEILISEARCH_KEY

DATA_DIR="/var/lib/postgresql/data"

if [ ! -s "${DATA_DIR}/PG_VERSION" ]; then
  mkdir -p "${DATA_DIR}"
  chown -R postgres:postgres "${DATA_DIR}"

  su - postgres -c "initdb -D ${DATA_DIR}"
  su - postgres -c "pg_ctl -D ${DATA_DIR} -o \"-c listen_addresses='*' -c shared_preload_libraries='vector'\" -w start"

  su - postgres -c "psql -v ON_ERROR_STOP=1 --username=postgres <<-EOSQL
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
        CREATE ROLE ${POSTGRES_USER} LOGIN PASSWORD '${POSTGRES_PASSWORD}';
      END IF;
    END
    \$\$;
EOSQL"

  su - postgres -c "psql -v ON_ERROR_STOP=1 --username=postgres <<-EOSQL
    SELECT 'CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\\gexec
EOSQL"

  su - postgres -c "psql -v ON_ERROR_STOP=1 -d ${POSTGRES_DB} <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL"

  su - postgres -c "psql -v ON_ERROR_STOP=1 -d ${POSTGRES_DB} -f /app/database/schema.sql" || true
  su - postgres -c "psql -v ON_ERROR_STOP=1 -d ${POSTGRES_DB} -f /app/database/ai_enterprise_schema.sql" || true

  su - postgres -c "pg_ctl -D ${DATA_DIR} -m fast -w stop"
fi

# Start supervisord
exec /usr/bin/supervisord -c /etc/supervisord.conf
