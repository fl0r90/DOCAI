#!/bin/bash
set -e

# --- CONFIGURARE ---
EXPORT_BASE="/mnt/xpenology/Proiect AI"
VERSION="v0.3.1_light"
EXPORT_DIR="$EXPORT_BASE/$VERSION"
PROJECT_DIR="/home/cfp-90/AI/V2"

echo "[*] Initializare export Forensic DocAI $VERSION la: $EXPORT_DIR"

# 1. Creare folder si testare acces cu SUDO
sudo mkdir -p "$EXPORT_DIR/images"
sudo touch "$EXPORT_DIR/test_write" && sudo rm "$EXPORT_DIR/test_write"
echo "[+] Acces de scriere pe Xpenology confirmat."

# 2. Export Imagini Docker (Fara volume uriase)
IMAGES=(
  "pgvector/pgvector:pg16"
  "redis:7-alpine"
  "neo4j:5-community"
  "ollama/ollama:latest"
  "v2-backend:latest"
  "v2-worker:latest"
  "v2-frontend:latest"
)

for IMG in "${IMAGES[@]}"; do
  FILENAME=$(echo $IMG | tr '/:' '_').tar
  if [ ! -f "$EXPORT_DIR/images/$FILENAME" ]; then
    echo "[+] Salvam $IMG -> $EXPORT_DIR/images/$FILENAME"
    sudo docker save "$IMG" -o "$EXPORT_DIR/images/$FILENAME"
  else
    echo "[-] Imaginea $IMG exista deja pe Xpenology."
  fi
done

# 3. Arhivare Configurații și Cod (Fara models/, data/, ocr_cache/)
echo "[*] Arhivare configuratii si cod sursa..."
sudo tar -czf "$EXPORT_DIR/forensic_docai_core.tar.gz" \
    -C "$PROJECT_DIR" \
    --exclude='data/*' \
    --exclude='models/*' \
    --exclude='ocr_cache/*' \
    --exclude='shared_data/*' \
    --exclude='.git/*' \
    --exclude='node_modules/*' \
    backend/ \
    frontend/ \
    docker-compose.yml \
    ARHITECTURA.md \
    .env

# 4. Creare Setup Script pe Xpenology
cat <<EOF > setup_v4.sh
#!/bin/bash
echo "[*] Instalare Forensic DocAI $VERSION pe noua masina"
# Incarcare imagini
for f in ./images/*.tar; do
  echo "[+] Incarcare \$f..."
  docker load -i "\$f"
done
# Extragere cod
echo "[+] Dezarhivare nucleu..."
tar -xzf forensic_docai_core.tar.gz
echo "[+] Gata! Nu uita sa copiezi manual folderele data/ si models/ daca ai nevoie de ele."
EOF

sudo mv setup_v4.sh "$EXPORT_DIR/setup_v4.sh"
sudo chmod +x "$EXPORT_DIR/setup_v4.sh"

echo "[SUCCESS] Exportul light v0.3.1 a fost finalizat pe Xpenology!"
