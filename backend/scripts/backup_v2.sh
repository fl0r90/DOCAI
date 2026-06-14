#!/bin/bash
# backup_v2.sh - Rulat din interiorul containerului backend
# Face backup la ambele baze de date si la fisierele incarcate.

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/app/backups/manual/backup_$TIMESTAMP"
FINAL_FILE="/app/backups/manual/DOCAI_BACKUP_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[*] Incepere backup date la $TIMESTAMP..."

# 1. Backup Baze de Date (via DNS 'db')
echo "[+] Exportare auth_db..."
pg_dump -h db -U forensic_admin auth_db > "$BACKUP_DIR/auth_db.sql"

echo "[+] Exportare forensic_db..."
pg_dump -h db -U forensic_admin forensic_db > "$BACKUP_DIR/forensic_db.sql"

# 2. Backup Uploads
echo "[+] Arhivare uploads..."
if [ -d "/app/uploads" ]; then
    tar -czf "$BACKUP_DIR/uploads.tar.gz" -C /app/uploads .
else
    echo "[!] Folder uploads nu a fost gasit."
fi

# 3. Impachetare finala
echo "[+] Creare pachet final..."
tar -czf "$FINAL_FILE" -C "$BACKUP_DIR" .

# 4. Curatare temporara
rm -rf "$BACKUP_DIR"

echo "[OK] Backup finalizat: $FINAL_FILE"
# Pastram doar ultimele 5 backup-uri manuale pentru a nu umple discul
cd /app/backups/manual && ls -t DOCAI_BACKUP_*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null || true
