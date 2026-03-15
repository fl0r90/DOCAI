#!/bin/bash

# --- CONFIGURARE ---
IMPORT_DIR="./docker_images"
COMPOSE_FILE="docker-compose-offline.yml"

echo "[*] Initializare DOCAI V2 - Regim OFFLINE"

# 1. Verificare dependinte locale
if [ ! -d "$IMPORT_DIR" ]; then
    echo "[!] EROARE: Directorul $IMPORT_DIR nu a fost gasit."
    echo "Asigura-te ca ai copiat tot pachetul de pe stick."
    exit 1
fi

# 2. Incarcare imagini Docker
echo "[*] Incarcare imagini din pachetul offline..."
for TAR in "$IMPORT_DIR"/*.tar; do
    echo "[+] Loading $TAR..."
    docker load -i "$TAR"
done

# 3. Verificare Volume / Directoare
echo "[*] Verificare structura date..."
DIRS=("data" "models" "ocr_cache" "frontend/node_modules")
for DIR in "${DIRS[@]}"; do
    if [ ! -d "$DIR" ]; then
        echo "[!] ATENTIE: Directorul $DIR lipseste. Unele date pot fi absente."
    fi
done

# 4. Pornire sistem
echo "[*] Lansare containere..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[OK] Sistemul a fost lansat."
echo "Accesibil la: http://localhost:3000"
echo "API Backend: http://localhost:8000"
