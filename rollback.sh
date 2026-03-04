#!/bin/bash
# rollback.sh - Revenire la versiunea anterioară

echo "!!! DEBUT PROCEDURĂ ROLLBACK !!!"

if [ ! -f "./backups/rollback/db_snapshot.sql" ]; then
  echo "Eroare: Nu am găsit niciun snapshot pentru restore."
  exit 1
fi

echo "[1/3] Restaurare imagini Docker anterioare..."
gunzip -c ./backups/rollback/backend_snapshot.tar.gz | docker load
gunzip -c ./backups/rollback/frontend_snapshot.tar.gz | docker load

echo "[2/3] Restaurare bază de date..."
# Oprim serviciile care scriu în DB
docker compose stop backend worker
# Restaurăm DB
cat ./backups/rollback/db_snapshot.sql | docker compose exec -T db psql -U forensic_admin johnny_bravo_db

echo "[3/3] Repornire sistem..."
docker compose up -d

echo "--- ROLLBACK FINALIZAT. Sistemul a revenit la starea anterioară. ---"
