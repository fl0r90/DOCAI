#!/bin/bash
# restore_v2.sh - Rulat din interiorul containerului backend
# Restaurează datele dintr-un pachet DOCAI_BACKUP_...

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Eroare: Specificați fișierul de backup."
    exit 1
fi

TEMP_DIR="/tmp/restore_$(date +%s)"
mkdir -p "$TEMP_DIR"

echo "[*] Incepere restaurare din $BACKUP_FILE..."

# 1. Extragere pachet
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# 2. Restaurare Baze de Date
if [ -f "$TEMP_DIR/auth_db.sql" ]; then
    echo "[+] Restaurare auth_db..."
    # Stergem si recream schemele pentru a fi siguri de consistenta
    psql -h db -U forensic_admin -d postgres -c "DROP DATABASE IF EXISTS auth_db;"
    psql -h db -U forensic_admin -d postgres -c "CREATE DATABASE auth_db;"
    cat "$TEMP_DIR/auth_db.sql" | psql -h db -U forensic_admin auth_db
fi

if [ -f "$TEMP_DIR/forensic_db.sql" ]; then
    echo "[+] Restaurare forensic_db..."
    psql -h db -U forensic_admin -d postgres -c "DROP DATABASE IF EXISTS forensic_db;"
    psql -h db -U forensic_admin -d postgres -c "CREATE DATABASE forensic_db;"
    cat "$TEMP_DIR/forensic_db.sql" | psql -h db -U forensic_admin forensic_db
fi

# 3. Restaurare Uploads
if [ -f "$TEMP_DIR/uploads.tar.gz" ]; then
    echo "[+] Restaurare uploads..."
    # Folosim sudo daca e nevoie, dar in container ar trebui sa fie ok
    rm -rf /app/uploads/*
    tar -xzf "$TEMP_DIR/uploads.tar.gz" -C /app/uploads
fi

# 4. Curățare
rm -rf "$TEMP_DIR"

echo "[OK] Restaurare finalizată cu succes!"
