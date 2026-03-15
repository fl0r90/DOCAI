# Arhitectură Tehnică - Forensic DocAI V2

## 1. Infrastructură și Servicii (Stabilizat)
- **Networking:** S-a trecut de la IP-uri statice hardcodate la **rezoluție DNS prin nume de servicii** (ex: `db`, `redis`, `llm`, `neo4j`). Această schimbare previne blocarea conexiunilor la repornirea containerelor (unde IP-urile se pot schimba/inversa).
- **Porturi:**
  - **Frontend:** `3000` (Next.js)
  - **Backend API:** `8000` (FastAPI)
  - **Ollama (LLM):** `11440` (Extern) / `11434` (Intern)
  - **Postgres:** `5432` (Intern)
  - **Neo4j:** `7474` (HTTP) / `7687` (Bolt)

## 2. Pipeline Ingestie & Sincronizare Multi-DB
- **OCR 100% Offline:** Docling și RapidOCR sunt configurate să folosească exclusiv cache-ul local (`ocr_cache/`). Nu necesită internet la prima rulare a unui document.
- **Sincronizare Entități (Double-Write):**
  - Entitățile extrase de AI sunt salvate simultan în **Neo4j** (pentru relații complexe) și în **Postgres** (`master_entities` / `document_entity_links`) pentru interogări SQL rapide și consistența datelor.
- **Segmentare (Chunking):** `CHUNK_SIZE` fixat la **1500 caractere**.
- **Reziliență:** Mecanism de retry (2 încercări) per segment și salvare imediată a `raw_text` în Postgres post-OCR.

## 3. Motorul de Chat & Inteligență Hybridă
- **Prompting Agnostic (Universal):** Toate prompturile (Audit, Extracție, Rezumat) au fost refactorizate pentru a fi profesionale și compatibile cu orice model (Phi, Llama, Gemma, Mistral). Format obligatoriu:
  ```
  ### System: {Expert Forensic Objective}
  ### User: {Context + Question}
  ### Assistant:
  ```
- **Neo4j Integration:** Chat-ul interoghează acum automat graful de conexiuni pentru a identifica legături între entitățile menționate în întrebare (ex: dacă două firme apar în același document).
- **Prioritate Matematică (SQL First):** Cifrele din SQL (agregări `SUM`, `COUNT`, `MAX`) au prioritate absolută în fața textului narativ (RAG) pentru a preveni halucinațiile matematice ale LLM-ului.

## 4. Strategie Offline & Migrare
- **Portabilitate pe Stick:** Sistemul poate fi mutat pe alt calculator via SMB/USB prin pachetul de migrare creat.
- **Procedură Migrare:**
  1. Export imagini Docker în format `.tar` (`pack_v2.sh`).
  2. Copiere foldere date: `data/`, `models/`, `ocr_cache/`, `frontend/node_modules/`.
  3. **Important:** Link-urile simbolice din `ocr_cache` și `node_modules` trebuie rezolvate în fișiere reale (`cp -L` sau `rsync -L`) pentru compatibilitate cu sisteme de fișiere non-Linux (CIFS/NTFS).
  4. Lansare pe noul sistem via `setup_v2.sh` folosind `docker-compose-offline.yml`.

## 5. Mentenanță și Depanare
- **Audit Logic:** Backend-ul loghează `[*] RAW SQL JSON` pentru a vedea query-ul generat de AI.
- **Restart Prompt:** Modificările la nivel de logică LLM sau Prompting necesită `docker compose restart backend/worker` pentru aplicare.
- **Easter Egg:** Versiunea "v0.1 ALPHA" din UI afișează detalii despre autori la hover.
