#!/bin/bash
set -e

# --- CONFIGURARE ---
EXPORT_DIR="/media/cfp-90/5E96086296083CD1/Docai/portable_v0.3.1"
PROJECT_DIR="/home/cfp-90/AI/V2"

echo "[*] Initializare export COMPLET (fara modele) direct pe SSD Windows: $EXPORT_DIR"

# 1. Creare structura
mkdir -p "$EXPORT_DIR/images"

# 2. Export Imagini Docker
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
    echo "[+] Salvam imaginea $IMG -> $EXPORT_DIR/images/$FILENAME"
    sudo docker save "$IMG" -o "$EXPORT_DIR/images/$FILENAME"
  else
    echo "[-] Imaginea $IMG exista deja."
  fi
done

# 3. Arhivare tot (Cod + Date + Cache) - FARA MODELE
echo "[*] Arhivare cod sursa, date si cache (fara modele)..."
sudo tar -czf "$EXPORT_DIR/forensic_docai_full_no_models.tar.gz" \
    -C "$PROJECT_DIR" \
    --exclude='models/*' \
    --exclude='.git/*' \
    --exclude='node_modules/*' \
    --exclude='*.tar' \
    . 

# 4. Copiere Configs (ca sa fie si la vedere, nu doar in arhiva)
cp "$PROJECT_DIR/docker-compose.yml" "$PROJECT_DIR/.env" "$PROJECT_DIR/ARHITECTURA.md" "$EXPORT_DIR/"

# 5. Creare Setup Script
cat <<EOF > "$EXPORT_DIR/setup_portable.sh"
#!/bin/bash
echo "[*] Instalare Forensic DocAI Portable v0.3.1"
# Incarcare imagini
for f in ./images/*.tar; do
  echo "[+] Incarcare \$f..."
  docker load -i "\$f"
done
# Extragere date si cod
if [ ! -f "forensic_docai_full_no_models.tar.gz" ]; then
    echo "[!] Eroare: Arhiva principala lipseste!"
    exit 1
fi
echo "[+] Dezarhivare nucleu si date..."
tar -xzf forensic_docai_full_no_models.tar.gz
echo "[+] Gata! Nu uita sa pui folderul 'models/' in radacina inainte de pornire."
echo "[+] Ruleaza: docker-compose up -d"
EOF

chmod +x "$EXPORT_DIR/setup_portable.sh"

echo "[SUCCESS] Pachetul portabil a fost creat pe SSD-ul de Windows!"
