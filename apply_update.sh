#!/bin/bash
# apply_update.sh - Mașina Offline
PACKAGE=$1
if [ -z "$PACKAGE" ]; then
  echo "Eroare: Specificați fișierul de update (.tar.gz)"
  exit 1
fi

echo "--- [1/4] Creare Snapshot pentru siguranță ---"
mkdir -p ./backups/rollback

# Backup Baze de Date
docker compose exec -T db pg_dump -U forensic_admin auth_db > ./backups/rollback/auth_db_snapshot.sql
docker compose exec -T db pg_dump -U forensic_admin forensic_db > ./backups/rollback/forensic_db_snapshot.sql

# Backup Imagini Docker Curente
echo "[*] Salvare imagini curente pentru rollback..."
docker save v2-backend:latest | gzip > ./backups/rollback/backend_snapshot.tar.gz
docker save v2-worker:latest | gzip > ./backups/rollback/worker_snapshot.tar.gz
docker save v2-frontend:latest | gzip > ./backups/rollback/frontend_snapshot.tar.gz

echo "--- [2/4] Extragere și Încărcare Update Nou ---"
# Încărcăm imaginile direct din pachet (presupunem că pachetul este un .tar.gz de imagini sau le conține)
if [[ "$PACKAGE" == *.tar.gz ]]; then
    echo "[+] Incarcare imagini din $PACKAGE..."
    gunzip -c "$PACKAGE" | docker load
else
    echo "[!] Format pachet necunoscut. Incercare docker load directa..."
    docker load -i "$PACKAGE"
fi

echo "--- [3/4] Aplicare Migrări și Restart ---"
# Forțăm recrearea containerelor cu noile imagini
docker compose up -d --remove-orphans

# Verificare dacă containerele au pornit cu succes
if [ $? -eq 0 ]; then
  echo "--- [4/4] Update finalizat cu succes! ---"
  # Curățăm pachetul de update dacă dorim (opțional)
else
  echo "!!! EROARE DETECTATĂ. Rulați ./rollback.sh pentru a reveni la starea anterioară !!!"
  exit 1
fi
