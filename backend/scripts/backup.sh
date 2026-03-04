#!/bin/bash
# Script pentru backup (DB sau Proiect Complet)
# Utilizare: ./backup.sh /cale/target nume_backup [db|full]

TARGET_DIR=${1:-"/app/backups/manual"}
BACKUP_NAME=${2:-"docai_backup_$(date +%Y%m%d_%H%M%S)"}
MODE=${3:-"full"} # db sau full
FINAL_PATH="$TARGET_DIR/$BACKUP_NAME"
PROGRESS_FILE="$FINAL_PATH/progress.log"

mkdir -p "$FINAL_PATH"
touch "$PROGRESS_FILE"

echo "0% | START | 0 B/s" > "$PROGRESS_FILE"

# 1. Backup Baza de Date (mereu inclus)
DB_SIZE=$(psql -h db -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT pg_database_size('${POSTGRES_DB}');" | xargs)
echo "Exportare baza de date ($MODE mode)..."
pg_dump -h db -U ${POSTGRES_USER} ${POSTGRES_DB} | \
pv -n -s "$DB_SIZE" 2> >(while read line; do echo "$line% | DB_DUMP | $(date +%T)" > "$PROGRESS_FILE"; done) > "$FINAL_PATH/database.sql"

if [ "$MODE" = "full" ]; then
    # 2. Backup Fișiere Proiect (Cod + Uploads + Config)
    # În container, /project_root va fi mapat către rădăcina proiectului de pe host
    echo "Arhivare proiect complet..."
    
    # Estimăm dimensiunea (excluzând folderele gigantice precum models, node_modules, .next)
    FILES_SIZE=$(du -sb /project_root --exclude="/project_root/models" --exclude="/project_root/frontend/node_modules" --exclude="/project_root/frontend/.next" --exclude="/project_root/data/postgres_data" | cut -f1)
    
    tar -cf - -C /project_root . \
        --exclude="./models" \
        --exclude="./frontend/node_modules" \
        --exclude="./frontend/.next" \
        --exclude="./data/postgres_data" \
        --exclude="./backups" | \
    pv -n -s "$FILES_SIZE" 2> >(while read line; do echo "$line% | PROJECT_ARCHIVE | $(date +%T)" > "$PROGRESS_FILE"; done) | \
    gzip > "$FINAL_PATH/project_full.tar.gz"
fi

echo "100% | SUCCESS | $(date +%T)" > "$PROGRESS_FILE"
chmod -R 777 "$FINAL_PATH"
