#!/bin/bash

echo "[*] Preparing Forensic DocAI Export for Cloud (RunPod)..."

# Numele arhivei
EXPORT_NAME="forensic_cloud.tar.gz"

# Excludem folderele mari
EXCLUDES=(
    "--exclude=models"
    "--exclude=data"
    "--exclude=ocr_cache"
    "--exclude=node_modules"
    "--exclude=.next"
    "--exclude=.git"
    "--exclude=backend/__pycache__"
    "--exclude=shared_uploads/*"
)

# Creăm arhiva
tar "${EXCLUDES[@]}" -czf "$EXPORT_NAME" .

echo "[+] Export complete: $EXPORT_NAME"
echo "[*] Instructions for RunPod:"
echo "1. Upload $EXPORT_NAME to your Pod via SCP or RunPod's Web File Manager."
echo "2. Extract: tar -xzf $EXPORT_NAME"
echo "3. Run: docker compose -f docker-compose-cloud.yml up --build -d"
echo "4. Access Frontend via Proxy Port 3000"
