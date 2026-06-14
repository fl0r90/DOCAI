# Ghid de Configurare Forensic DocAI pe RunPod (Bare Metal)
*Creat pe 29 Martie 2026 - Versiunea v0.3.0 Snapshot*

Acest document conține toate comenzile necesare pentru a recrea mediul de investigație pe un Pod RunPod (recomandat RTX 4090/5090).

## 1. Pregătire Sistem (OS)
Rulează aceste comenzi în terminalul Jupyter imediat după ce pornești Pod-ul:
```bash
apt update && apt install -y postgresql postgresql-contrib redis-server curl gnupg build-essential screen
# Instalare pgvector (esențial)
apt install -y postgresql-16-pgvector
# Pornire servicii
service postgresql start
service redis-server start
# Instalare Ollama
curl -fsSL https://ollama.com/install.sh | sh
nohup ollama serve > ollama.log 2>&1 &
# Descarcare Model 32B (Reasoning de top)
ollama pull deepseek-r1:32b
```

## 2. Inițializare Baze de Date
Rulează aceste comenzi SQL pentru a crea structura (SQL-ul „nuclear”):
```bash
su - postgres -c "psql -c \"CREATE USER forensic_admin WITH PASSWORD 'supersecret_dgx_password' SUPERUSER;\""
su - postgres -c "psql -c \"CREATE DATABASE auth_db OWNER forensic_admin;\""
su - postgres -c "psql -c \"CREATE DATABASE forensic_db OWNER forensic_admin;\""
su - postgres -c "psql -d forensic_db -c \"CREATE EXTENSION IF NOT EXISTS vector;\""

# Creare tabele manual (Workaround pentru erori SQLAlchemy)
su - postgres -c "psql -d forensic_db -c \"
CREATE TABLE IF NOT EXISTS cases (id SERIAL PRIMARY KEY, name VARCHAR, description TEXT, master_id INTEGER, status VARCHAR DEFAULT 'OPEN', created_at TIMESTAMP WITH TIME ZONE DEFAULT now());
CREATE TABLE IF NOT EXISTS documents (id SERIAL PRIMARY KEY, filename VARCHAR, file_hash VARCHAR, case_id INTEGER REFERENCES cases(id), user_id INTEGER, status VARCHAR DEFAULT 'QUEUED', doc_type VARCHAR, doc_metadata JSON, raw_text TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT now());
CREATE TABLE IF NOT EXISTS document_storage (id UUID PRIMARY KEY, parent_doc_id UUID, content_text TEXT NOT NULL, embedding vector(1024), raw_metadata JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT now());
CREATE TABLE IF NOT EXISTS financial_items (id VARCHAR PRIMARY KEY, document_id INTEGER REFERENCES documents(id), description TEXT, amount DOUBLE PRECISION, currency VARCHAR DEFAULT 'RON', transaction_date VARCHAR, created_at TIMESTAMP WITH TIME ZONE DEFAULT now());
CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR UNIQUE, hashed_password VARCHAR, role VARCHAR, needs_password_change INTEGER DEFAULT 0, created_at TIMESTAMP WITH TIME ZONE DEFAULT now());
CREATE TABLE IF NOT EXISTS system_settings (id SERIAL PRIMARY KEY, key VARCHAR UNIQUE, value VARCHAR);
INSERT INTO users (username, hashed_password, role, needs_password_change) VALUES ('master', '\$2b\$12\$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6L6s57OTWzKuonhK', 'MASTER', 0); -- Parola: master
\""
```

## 3. Fix-uri de Cod (Chirurgie prin Terminal)
Trebuie aplicate după ce extragi arhiva în `/workspace`:
```bash
# 1. Dezactivare Neo4j (care bloca pornirea)
sed -i 's/graph_service.verify_constraints()/# graph_service.verify_constraints()/g' /workspace/backend/core_engine/main.py

# 2. Fix parametru 'temperature' în grinder.py
sed -i 's/def _send_to_ollama(model: str, prompt: str, timeout: int, is_json: bool = False, keep_warm: bool = True):/def _send_to_ollama(model: str, prompt: str, timeout: int, is_json: bool = False, keep_warm: bool = True, **kwargs):/g' /workspace/backend/core_engine/services/grinder.py

# 3. Fix extragere pagini (să nu confunde anul 2026 cu pagina 2026)
sed -i "s/p = re.findall(r'\\\\d+', resp)/p_match = re.search(r'GET_PAGE_CONTEXT\\\\((\\\\d+),\\\\s*(\\\\d+)\\\\)', resp, re.IGNORECASE); p = [p_match.group(1), p_match.group(2)] if p_match else []/g" /workspace/backend/core_engine/services/chat_service.py

# 4. Setare localhost în loc de 'db'
sed -i 's/db:5432/localhost:5432/g' /workspace/backend/core_engine/database.py
```

## 4. Pornire Aplicație
```bash
# Pornire Backend (în Jupyter)
cd /workspace/backend && export PYTHONPATH=$PYTHONPATH:. && uvicorn core_engine.main:app --host 0.0.0.0 --port 8000

# Pornire Frontend (în Jupyter)
cd /workspace/frontend && npm run dev -- -p 3000
```

## 5. Tunel SSH (Pe Laptopul tău)
```bash
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 root@{IP} -p {PORT}
```
*Accesează: http://localhost:3000*
