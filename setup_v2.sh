#!/bin/bash

# setup_v2.sh - Script pentru configurarea mediului și pre-încărcarea modelelor OCR
# Acest script asigură că sistemul poate rula ulterior complet OFFLINE.

echo "--- [1/5] Creare structură foldere locale ---"
mkdir -p data/postgres_data
mkdir -p data/redis_data
mkdir -p data/uploads
mkdir -p data/archive
mkdir -p ocr_cache
mkdir -p backups
mkdir -p updates
echo "[+] Foldere create."

echo "--- [2/5] Construire imagini Docker ---"
# Încărcăm variabilele din .env dacă există
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

docker compose build
echo "[+] Imagini construite cu succes."

echo "--- [3/5] Pre-încărcare modele OCR (Docling/HuggingFace) ---"
echo "Acest pas necesită conexiune la internet. Se descarcă aproximativ 1-2 GB de modele..."

# Rulăm containerul de backend cu internet activ (HF_OFFLINE=0)
# Mapăm volumul local ocr_cache pentru a persista download-ul pe host
docker run --rm \
    -v "$(pwd)/ocr_cache:/app/ocr_cache" \
    -e HF_OFFLINE=0 \
    -e HF_HOME=/app/ocr_cache/huggingface \
    v2-backend python3 preload_ocr.py

if [ $? -eq 0 ]; then
    echo "[+] Modele OCR descărcate și salvate în ./ocr_cache."
else
    echo "[-] EROARE la descărcarea modelelor OCR. Verificați conexiunea la internet."
    exit 1
fi

echo "--- [4/5] Pregătire modele LLM (Ollama) ---"
# Pornim temporar serviciul llm pentru a descărca modelul default
docker compose up -d llm
echo "Așteptăm ca Ollama să pornească..."
sleep 5
echo "Descărcăm modelul LLM default (qwen2.5:7b) și modelul de embeddings (mxbai-embed-large)..."
docker compose exec llm ollama pull qwen2.5:7b
docker compose exec llm ollama pull mxbai-embed-large
echo "[+] Modele LLM și Embeddings pregătite."

echo "--- [5/5] Finalizare ---"
docker compose down

echo "===================================================="
echo " SETUP FINALIZAT CU SUCCES! "
echo "===================================================="
echo "Puteți porni sistemul acum (chiar și fără internet):"
echo "  docker compose up -d"
echo "===================================================="
