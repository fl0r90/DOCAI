#!/bin/bash
# rollback.sh - Revenire la versiunea anterioară

echo "!!! DEBUT PROCEDURĂ ROLLBACK !!!"

if [ ! -f "./backups/rollback/auth_db_snapshot.sql" ]; then
  echo "Eroare: Nu am găsit niciun snapshot pentru restore."
  exit 1
fi

echo "[1/3] Restaurare imagini Docker anterioare..."
# Restaurăm toate imaginile salvate înainte de update
gunzip -c ./backups/rollback/backend_snapshot.tar.gz | docker load
gunzip -c ./backups/rollback/worker_snapshot.tar.gz | docker load
gunzip -c ./backups/rollback/frontend_snapshot.tar.gz | docker load

echo "[2/3] Restaurare baze de date..."
# Oprim serviciile care scriu în DB pentru a evita coruperea datelor în timpul restaurării
docker compose stop backend worker

# Restaurăm auth_db
echo "[*] Restaurare auth_db..."
cat ./backups/rollback/auth_db_snapshot.sql | docker compose exec -T db psql -U forensic_admin auth_db

# Restaurăm forensic_db
echo "[*] Restaurare forensic_db..."
cat ./backups/rollback/forensic_db_snapshot.sql | docker compose exec -T db psql -U forensic_admin forensic_db

echo "[3/3] Repornire sistem..."
# Forțăm repornirea serviciilor cu imaginile vechi reîncărcate
docker compose up -d

echo "--- ROLLBACK FINALIZAT. Sistemul a revenit la starea anterioară. ---"
