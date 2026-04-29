#!/usr/bin/env bash
# Append pg_partman_bgw to shared_preload_libraries via ALTER SYSTEM.
# Runs once at container init (before pg_partman extension CREATE in alembic 0010).
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER SYSTEM SET shared_preload_libraries = 'pg_partman_bgw';
    ALTER SYSTEM SET pg_partman_bgw.interval = '3600';
    ALTER SYSTEM SET pg_partman_bgw.role = '$POSTGRES_USER';
    ALTER SYSTEM SET pg_partman_bgw.dbname = '$POSTGRES_DB';
EOSQL
