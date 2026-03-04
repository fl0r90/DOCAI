import os
import requests
import json
import redis
import re
from sqlalchemy import text
from ..database import engine, SessionLocal
from ..core.config import get_active_model_name
from ..models import DocumentChunk, Document, ChatMessage

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)

SCHEMA_PROMPT = "PostgreSQL: documents, master_entities. Filter by case_id={case_id}. Return ONLY SQL."

def _unload_all_models():
    try:
        res = requests.get(f"{OLLAMA_URL}/api/ps")
        if res.status_code == 200:
            for m in res.json().get("models", []):
                requests.post(f"{OLLAMA_URL}/api/generate", json={"model": m['name'], "keep_alive": 0}, timeout=5)
    except: pass

def _generate_query_vector(text: str):
    try:
        # Embeddings folosesc keep_alive scurt pentru a nu bloca GPU inutil
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": "mxbai-embed-large", "prompt": text, "keep_alive": 60
        }, timeout=60)
        return response.json().get("embedding", [])
    except: return []

def _extract_json(text):
    try:
        start = text.find('{'); end = text.rfind('}')
        if start != -1 and end != -1: return json.loads(text[start:end+1])
        return None
    except: return None

def _format_prompt(model_name: str, system_msg: str, user_msg: str, history: str = ""):
    m = model_name.lower()
    if "llama3" in m: return f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_msg}\nContext: {history}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_msg}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    if "gemma" in m: return f"<start_of_turn>user\nSYSTEM: {system_msg}\nCONTEXT: {history}\nQUESTION: {user_msg}<end_of_turn>\n<start_of_turn>model\n"
    return f"<|im_start|>system\n{system_msg}\nContext: {history}<|im_end|>\n<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n"

def query_investigator(case_id: int, user_question: str):
    # 1. SEMNALIZARE PRIORITATE CHAT: Blocăm worker-ul timp de 2 minute de inactivitate
    r.setex("llm_active_session", 120, "true")
    
    # 2. Eliberăm orice model de fundal (Qwen) dacă e cazul
    # Doar dacă modelul de chat este diferit de cel de extracție sau pentru a curăța memoria
    _unload_all_models()
    
    active_model = get_active_model_name()
    
    history_context = ""
    with SessionLocal() as db:
        last_msgs = db.query(ChatMessage).filter(ChatMessage.case_id == case_id).order_by(ChatMessage.created_at.desc()).limit(4).all()
        for m in reversed(last_msgs): history_context += f"{m.role.upper()}: {m.content}\n"

    # 3. SQL ID (Modelul rămâne cald pentru pasul următor)
    doc_ids = []
    try:
        sys_sql = SCHEMA_PROMPT.replace('{case_id}', str(case_id)) + " Return ONLY SQL."
        sql_prompt = _format_prompt(active_model, sys_sql, f"ID for: {user_question}", history_context)
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": active_model, "prompt": sql_prompt, "stream": False, "keep_alive": 300
        }, timeout=60)
        sql = res.json().get("response", "").strip().replace("```sql", "").replace("```", "").strip()
        sql = re.sub(r'\bLIKE\b', 'ILIKE', sql, flags=re.IGNORECASE)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            doc_ids = [row[0] for row in result.fetchall()]
    except: pass

    # 4. RAG
    query_vector = _generate_query_vector(user_question)
    raw_context = ""
    with SessionLocal() as db:
        if query_vector:
            chunks = db.query(DocumentChunk).join(Document).filter(Document.case_id == case_id).order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(15).all()
            for d_id in doc_ids[:2]:
                headers = db.query(DocumentChunk).filter(DocumentChunk.document_id == d_id).order_by(DocumentChunk.id.asc()).limit(8).all()
                for h in headers:
                    if h.id not in [c.id for c in chunks]: chunks.append(h)
            for chunk in chunks: raw_context += f"\n--- PROBĂ: {chunk.document.filename} ---\n{chunk.content}\n"

    # 5. Final Answer (Modelul rămâne cald pentru întrebări consecutive)
    sys_final = "Forensic Auditor. JSON format."
    user_final = f"EVIDENCE:\n{raw_context}\n\nQUESTION: {user_question}"
    final_prompt = _format_prompt(active_model, sys_final, user_final, history_context)
    
    try:
        summary_res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": active_model, "prompt": final_prompt, "stream": False, "format": "json", 
            "keep_alive": 600, # Ținem modelul de chat încărcat 10 minute
            "options": {"temperature": 0.1, "num_ctx": 16384}
        }, timeout=300)
        
        parsed = _extract_json(summary_res.json().get("response", "{}"))
        
        # Nu ștergem semnalul aici, îl lăsăm să expire natural (TTL 120s) pentru a permite dialog rapid
        
        if parsed: return { "answer": parsed.get("answer", ""), "citations": parsed.get("citations", []), "results": [] }
        return { "answer": summary_res.json().get("response", ""), "citations": [], "results": [] }
    except Exception as e:
        return { "answer": f"Eroare Analiză: {str(e)}" }
