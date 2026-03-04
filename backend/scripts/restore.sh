#!/bin/bash
# Script pentru restaurare backup
# Utilizare: ./restore.sh /cale/catre/folder_backup

BACKUP_PATH=$1

if [ -z "$BACKUP_PATH" ]; then
    echo "Eroare: Trebuie sa specifici calea catre folderul de backup."
    echo "Exemplu: ./restore.sh /app/backups/manual/docai_backup_20240101_120000"
    exit 1
fi

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Eroare: Directorul de backup nu exista: $BACKUP_PATH"
    exit 1
fi

echo "Incepere restaurare din: $BACKUP_PATH"

# 1. Restaurare Baza de Date
echo "Restaurare baza de date..."
# Nota: dropdb/createdb ar fi mai sigure, dar folosim psql direct pentru simplitate in acest context
# Se presupune ca suntem intr-un container care are acces la 'db'
psql -h db -U ${POSTGRES_USER} -d ${POSTGRES_DB} < "$BACKUP_PATH/database.sql"

if [ $? -eq 0 ]; then
    echo "Baza de date restaurata cu succes."
else
    echo "EROARE la restaurarea bazei de date!"
    exit 1
fi

# 2. Restaurare Fisiere
echo "Restaurare fisiere uploads..."
# Stergem continutul curent pentru a evita conflicte (optional, depinde de politica)
# rm -rf /app/uploads/*
tar -xzf "$BACKUP_PATH/files.tar.gz" -C /app/uploads

if [ $? -eq 0 ]; then
    echo "Fisiere restaurate cu succes."
else
    echo "EROARE la restaurarea fisierelor!"
    exit 1
fi

echo "Restaurare finalizata cu succes."
