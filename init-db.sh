#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE auth_db;
    CREATE DATABASE forensic_db;
    GRANT ALL PRIVILEGES ON DATABASE auth_db TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE forensic_db TO $POSTGRES_USER;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "forensic_db" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
