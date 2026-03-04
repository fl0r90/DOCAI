#!/bin/bash
# pack_v2.sh - Rulează asta pe mașina CU internet pentru a pregăti pachetul
VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Specificați versiunea: ./pack_v2.sh 1.1"
  exit 1
fi

echo "--- Împachetare DocAI Versiunea $VERSION ---"

# 1. Salvare imagini Docker
echo "[1/3] Salvare imagini Docker..."
docker save v2-backend:latest | gzip > images_backend_$VERSION.tar.gz
docker save v2-frontend:latest | gzip > images_frontend_$VERSION.tar.gz

# 2. Creare arhivă cod și configurări (Include scripturi și modele OCR)
echo "[2/3] Împachetare configurări, scripturi și modele OCR..."
tar -czvf update_bundle_$VERSION.tar.gz \
    docker-compose.yml \
    setup_v2.sh \
    apply_update.sh \
    rollback.sh \
    .env \
    backend/ \
    frontend/ \
    ocr_cache/

echo "--- GATA! Copiați fișierele .tar.gz pe stick-ul USB ---"
echo "Fișiere create:"
echo " - images_backend_$VERSION.tar.gz (Imagine Backend)"
echo " - images_frontend_$VERSION.tar.gz (Imagine Frontend)"
echo " - update_bundle_$VERSION.tar.gz (Cod, scripturi și MODELE OCR)"
