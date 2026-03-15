import os
import requests
import json
import redis
import re
import time
from sqlalchemy import text, or_
from ..database import engine, SessionLocal
from ..core.config import get_llm_config
from ..models import DocumentChunk, Document, ChatMessage

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)

# Schema bazei de date (PostgreSQL)
SCHEMA_PROMPT = """
Sistem Audit Forensic. Schema tabele:
- documents (id, filename, case_id)
- financial_items (id, document_id, description, amount, currency)

INSTRUCTIUNE CRITICA: Daca intrebarea utilizatorului implica cifre, sume, numar de tranzactii sau cautari de magazine, ESTE OBLIGATORIU sa generezi o interogare SQL.
REGULA SQL: Cauta magazinele folosind operatorul ILIKE cu wildcard-uri (ex: description ILIKE '%nume%').
REGULA FILTRU: Filtreaza intotdeauna dupa documents.case_id = {case_id} folosind JOIN.
FORMAT RASPUNS: Returneaza EXCLUSIV un obiect JSON de tipul: {"sql": "SELECT..."}
"""

def get_active_model_name():
    try: return get_llm_config()["active_model"]
    except: return "mistral-nemo:12b"

def _generate_query_vector(text: str):
    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "mxbai-embed-large", "prompt": text}, timeout=60)
        return response.json().get("embedding", [])
    except: return []

def _extract_json(text):
    try:
        if not text: return None
        # Curățare tag-uri (DeepSeek, etc.)
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Căutare JSON în blocuri de cod sau text brut
        json_match = re.search(r'```json\s*(.*?)\s*```', clean, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
        if json_match:
            json_str = json_match.group(1) if "```json" in clean else json_match.group(0)
            return json.loads(json_str)
        return None
    except: return None

def _format_prompt(model_name: str, system_msg: str, user_msg: str, history: str = ""):
    """Format universal de prompt pentru compatibilitate cu orice LLM (Mistral, Llama, Phi, Gemma)."""
    return f"""### System:
{system_msg}

### Context History:
{history}

### User:
{user_msg}

### Assistant:
"""

from ..services.graph_service import graph_service

def query_investigator(case_id: int, user_question: str):
    try:
        r.setex("llm_active_session", 120, "true")
        active_model = get_active_model_name()
        
        history_context = ""
        with SessionLocal() as db:
            last_msgs = db.query(ChatMessage).filter(ChatMessage.case_id == case_id).order_by(ChatMessage.created_at.desc()).limit(4).all()
            for m in reversed(last_msgs):
                history_context += f"{m.role.upper()}: {m.content}\n"

        # 1. SQL Discovery (Mathematical Accuracy)
        sql_facts = ""
        sql_generated = None
        try:
            sys_sql = f"""Expert Auditor Forensic - SQL Generator.
Schema: 
- documents (id, filename, case_id)
- financial_items (id, document_id, description, amount, currency)

Obiectiv: Generează un query PostgreSQL valid pentru a răspunde întrebării.
Reguli:
- Folosește 'ILIKE %termen%' pentru descrieri.
- Filtrează obligatoriu după case_id = {case_id} prin JOIN.
- Returnează EXCLUSIV un obiect JSON: {{"sql": "query"}}"""
            
            sql_prompt = f"### System:\n{sys_sql}\n\n### User:\n{user_question}\n\n### Assistant:\n"
            
            res_sql = requests.post(f"{OLLAMA_URL}/api/generate", json={
                "model": active_model, "prompt": sql_prompt, "stream": False, "format": "json",
                "options": {"temperature": 0.0}
            }, timeout=60)
            
            raw_response = res_sql.json().get("response", "{}")
            print(f"[*] RAW SQL JSON: {raw_response}")
            
            sql_json = json.loads(raw_response)
            sql = sql_json.get("sql", "").strip()
            
            if sql and sql.lower().startswith("select"):
                sql_generated = sql
                sql = sql.replace(';', '').replace('\\', '')
                print(f"[*] AI Executing SQL: {sql}")
                with engine.connect() as conn:
                    result = conn.execute(text(sql))
                    rows = result.fetchall()
                    
                    if rows:
                        # Valoare unica (SUM, COUNT)
                        if len(rows) == 1 and len(rows[0]) == 1:
                            val = rows[0][0] if rows[0][0] is not None else 0
                            if isinstance(val, float): val = round(val, 2)
                            sql_facts = f"--- DATE MATEMATICE CERTIFICATE (SQL) ---\nRezultat: {val}\n\n"
                        else:
                            # Lista de rezultate
                            sql_facts = "--- DATE EXTRASE DIN TABELE (SQL) ---\n"
                            for r_item in rows[:10]:
                                sql_facts += f"- {' | '.join(str(x) for x in r_item)}\n"
                            sql_facts += "\n"
        except Exception as e:
            print(f"[!] SQL Runtime Error: {e}")

        # 2. Graph Discovery (Neo4j)
        graph_facts = ""
        try:
            # Extragem entitati potentiale
            potential_entities = re.findall(r'"([^"]+)"', user_question) 
            if not potential_entities:
                potential_entities = re.findall(r'\b[A-Z][A-Za-z0-9\.]+(?:\s+[A-Z][A-Za-z0-9\.]+)*\b', user_question)
            
            if potential_entities:
                cleaned_entities = [e.strip() for e in potential_entities if len(e) > 3]
                graph_res = graph_service.query_relationships(cleaned_entities)
                if graph_res:
                    graph_facts = f"--- RELATII SI CONEXIUNI IDENTIFICATE (GRAF) ---\n{graph_res}\n\n"
        except Exception as e_graph:
            print(f"[!] Graph Query Error: {e_graph}")

        # 3. RAG Context (Similarity Search)
        query_vector = _generate_query_vector(user_question)
        raw_context = sql_facts + graph_facts
        
        with SessionLocal() as db:
            keywords = [w.strip(",.!?") for w in user_question.split() if len(w) > 3]
            keywords.extend(re.findall(r'\b\d{3,}\b', user_question))
            if keywords:
                filters = [DocumentChunk.content.ilike(f"%{kw}%") for kw in set(keywords)]
                kw_chunks = db.query(DocumentChunk).join(Document).filter(Document.case_id == case_id, or_(*filters)).limit(15).all()
                for kc in kw_chunks:
                    raw_context += f"\n--- FRAGMENT PROBA: {kc.document.filename} ---\n{kc.content}\n"

        # 4. Final Answer Generation
        sys_final = """Senior Forensic Auditor & Analyst.
Misiune: Oferă un răspuns riguros, bazat exclusiv pe contextul furnizat.
Priorități:
1. Datele matematice din SQL reprezintă sursa supremă de adevăr pentru cifre.
2. Relațiile din graf explică conexiunile între entități.
3. Fragmentele de probă oferă detalii contextuale narative.
Instrucțiune: Dacă există contradicții între SQL și textul narativ, prevalează cifrele din SQL. Răspunde în ROMÂNĂ."""
        
        user_final = f"CONTEXT:\n{raw_context}\n\nINTREBARE UTILIZATOR: {user_question}"
        final_prompt = _format_prompt(active_model, sys_final, user_final, history_context)
        
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": active_model, "prompt": final_prompt, "stream": False,
            "options": {"num_ctx": 8192}
        }, timeout=300)
        resp_text = res.json().get("response", "").strip()
        
        # Extragem raspunsul curat 
        answer = resp_text
        parsed = _extract_json(resp_text)
        if parsed: answer = parsed.get("answer", resp_text)
        
        return { 
            "answer": answer, 
            "sql": sql_generated, 
            "citations": [], 
            "results": [] 
        }

    except Exception as e:
        print(f"[!] Critical Chat Error: {e}")
        return { "answer": f"Eroare sistem audit: {str(e)}", "sql": None }
