#!/bin/bash

echo "[*] Incepere curatare selectiva pentru export..."

# 1. GOLIRE FORENSIC_DB (Postgres) - pastram AUTH_DB (Userii)
docker exec v2-db-1 psql -U forensic_admin -d forensic_db -c "
TRUNCATE TABLE financial_items, document_entity_links, master_entities, chat_messages, document_chunks, audit_logs, documents, cases CASCADE;
"

# 2. GOLIRE NEO4J (Graf)
docker exec v2-neo4j cypher-shell -u neo4j -p supersecret_dgx_password "MATCH (n) DETACH DELETE n;"

# 3. STERGERE DOSARE DOCUMENTE SI CACHE
sudo rm -rf data/uploads/* 
sudo rm -rf data/neo4j_data/* 
sudo rm -rf data/neo4j_logs/*
sudo rm -rf data/redis_data/*
sudo rm -rf uploads/*
sudo rm -rf backend/uploads/*

echo "[OK] Datele forensic au fost sterse. Userii din auth_db au fost PASTRATI."
