#!/bin/bash

# --- CONFIGURARE ---
EXPORT_DIR="/mnt/docai_migration/docker_images"
PROJECT_DIR="/home/cfp-90/AI/V2"
mkdir -p "$EXPORT_DIR"

echo "[*] Incepere export imagini pentru migrare offline la $EXPORT_DIR..."

# 1. Imagile de baza (Third-party)
IMAGES=(
  "pgvector/pgvector:pg16"
  "redis:7-alpine"
  "neo4j:5-community"
  "ollama/ollama:latest"
)

for IMG in "${IMAGES[@]}"; do
  FILENAME=$(echo $IMG | tr '/:' '_').tar
  if [ ! -f "$EXPORT_DIR/$FILENAME" ]; then
    echo "[+] Exporting $IMG -> $EXPORT_DIR/$FILENAME"
    docker save $IMG -o "$EXPORT_DIR/$FILENAME"
  else
    echo "[-] $IMG deja exportat."
  fi
done

# 2. Imagile proiectului (Build actualizat)
echo "[*] Building project images..."
cd "$PROJECT_DIR"
docker compose build backend worker frontend

PROJECT_IMAGES=(
  "v2-backend:latest"
  "v2-worker:latest"
  "v2-frontend:latest"
)

for IMG in "${PROJECT_IMAGES[@]}"; do
  FILENAME=$(echo $IMG | tr '/:' '_').tar
  echo "[+] Exporting $IMG -> $EXPORT_DIR/$FILENAME"
  docker save $IMG -o "$EXPORT_DIR/$FILENAME"
done

echo "[OK] Toate imaginile au fost salvate in $EXPORT_DIR"
echo "[!] NU UITA SA COPIEZI SI DOSARELE MANUALE PE STICK (sau direct pe SMB):"
echo "    - data/"
echo "    - models/"
echo "    - ocr_cache/"
echo "    - frontend/node_modules/"
