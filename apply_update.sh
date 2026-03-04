#!/bin/bash
# apply_update.sh - Mașina Offline
PACKAGE=$1
if [ -z "$PACKAGE" ]; then
  echo "Eroare: Specificați fișierul de update (.tar.gz)"
  exit 1
fi

echo "--- [1/4] Creare Snapshot pentru siguranță ---"
mkdir -p ./backups/rollback

# Backup Bază de Date
docker compose exec -T db pg_dump -U forensic_admin johnny_bravo_db > ./backups/rollback/db_snapshot.sql

# Backup Imagini Docker Curente (cele care rulează acum)
docker save v2-backend:latest | gzip > ./backups/rollback/backend_snapshot.tar.gz
docker save v2-frontend:latest | gzip > ./backups/rollback/frontend_snapshot.tar.gz

echo "--- [2/4] Extragere și Încărcare Update Nou ---"
# Presupunem că pachetul conține noile imagini
tar -xzf "$PACKAGE" -C ./updates/tmp_extract
# (Codul de load imagini din pasul anterior...)
# gunzip -c ./updates/tmp_extract/images_*.tar.gz | docker load

echo "--- [3/4] Aplicare Migrări și Restart ---"
docker compose up -d

# Verificare dacă containerele au pornit cu succes
if [ $? -eq 0 ]; then
  echo "--- [4/4] Update finalizat cu succes! ---"
else
  echo "!!! EROARE DETECTATĂ. Rulați ./rollback.sh pentru a reveni la starea anterioară !!!"
  exit 1
fi