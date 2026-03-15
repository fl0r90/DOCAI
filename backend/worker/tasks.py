import time
import os
import redis
import json
import requests
import re
from sqlalchemy import text
from core_engine.database import ForensicSessionLocal, engine
from core_engine import models
from core_engine.services.ocr_service import process_document
from core_engine.services.grinder import extract_forensic_data
from core_engine.services.graph_service import graph_service

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

def check_llm_pause():
    return r.exists("llm_active_session")

def wait_for_llm(timeout=120):
    """Așteaptă ca motorul LLM să fie online și funcțional."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            res = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
            if res.status_code == 200: return True
        except: pass
        time.sleep(5)
    return False

def extract_financial_regex(text_content):
    """Extracție deterministică a tranzacțiilor folosind regex."""
    transactions = []
    pattern = r'\|\s*([0-9]{2}\s+[a-z]+\s+202[0-9])\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
    matches = re.finditer(pattern, text_content, re.IGNORECASE)
    for match in matches:
        try:
            suma_raw = match.group(3).strip().replace(',', '.')
            suma_clean = "".join(c for c in suma_raw if c.isdigit() or c == '.')
            suma_val = float(suma_clean)
            if suma_val > 0:
                transactions.append({
                    "descriere": f"{match.group(1).strip()} - {match.group(2).strip()}",
                    "suma": suma_val, "valuta": "RON"
                })
        except: continue
    return transactions

def are_descriptions_similar(d1, d2):
    """Verifică dacă două descrieri sunt similare bazat pe cuvinte cheie."""
    def get_tokens(text):
        if not text: return set()
        words = re.findall(r'\b[A-Z0-9]{3,}\b', str(text).upper())
        stop_words = {'CUMPARARE', 'PRIN', 'POS', 'AUTH', 'CODE', 'CARD', 'RON', 'EUR', 'PLATA', 'TRANSFER'}
        return {w for w in words if w not in stop_words}
    t1, t2 = get_tokens(d1), get_tokens(d2)
    if not t1 or not t2: return str(d1).strip().upper() == str(d2).strip().upper()
    intersection = t1.intersection(t2)
    return len(intersection) >= 2 or (len(t1) > 0 and len(intersection) / len(t1) > 0.6)

def _create_chunks_and_embeddings(doc_id, chunks):
    """Salvează fragmentele în DB și generează vectori cu management de memorie."""
    if not chunks: return
    print(f"[*] Procesare vectori pentru {len(chunks)} chunks (document {doc_id})...")
    
    # Eliberăm VRAM înainte de embeddings
    try: requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "gemma2:27b", "keep_alive": 0}, timeout=5)
    except: pass
    
    db = ForensicSessionLocal()
    try:
        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc_id).delete()
        db.commit()

        for idx, content in enumerate(chunks):
            if not content or len(content.strip()) < 5: continue
            safe_content = "".join(c for c in content if c.isprintable() or c in "\n\r\t")
            embedding_prompt = safe_content[:800]
            
            # Retry logic pentru embeddings
            for attempt in range(3):
                try:
                    res = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
                        "model": "mxbai-embed-large", "prompt": embedding_prompt, "keep_alive": 300
                    }, timeout=60)
                    if res.status_code == 200:
                        embedding = res.json().get("embedding")
                        if embedding:
                            new_chunk = models.DocumentChunk(document_id=doc_id, content=safe_content, page_number=1, embedding=embedding)
                            db.add(new_chunk); break
                except: time.sleep(5)
        
        db.commit()
        try: requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "mxbai-embed-large", "keep_alive": 0}, timeout=5)
        except: pass
    finally:
        db.close()

def worker_loop():
    print("[*] Worker Forensic v3.0 (Zero-Block Resilience) pornit.")
    
    while True:
        if check_llm_pause():
            time.sleep(10); continue

        db = ForensicSessionLocal()
        next_doc = None
        try:
            next_doc = db.query(models.Document).filter(models.Document.status.in_(["QUEUED", "AI_EXTRACTING", "PROCESSING"]))\
                .order_by(models.Document.created_at.asc()).first()

            if not next_doc:
                db.close(); time.sleep(5); continue

            doc_id = next_doc.id
            filename = next_doc.filename
            
            # Pas 1: OCR & Chunking
            if next_doc.status == "QUEUED":
                next_doc.status = "PROCESSING"; db.commit()
                file_path = os.path.join("/app/uploads", filename)
                if not os.path.exists(file_path): file_path = os.path.join("/app/backend/uploads", filename)
                
                ocr_result = process_document(file_path)
                if isinstance(ocr_result, dict):
                    next_doc.raw_text = ocr_result.get("markdown", "")
                    db.commit() # Salvare imediată a textului OCR
                    _create_chunks_and_embeddings(doc_id, ocr_result.get("chunks", []))
                
                next_doc.status = "AI_EXTRACTING"; db.commit()
            
            # Pas 2: Analiza AI (cu Reluare din Redis)
            print(f"[*] Analiza Rezilienta pentru {filename}...")
            
            # Citim progresul existent din Redis (dacă există)
            saved_progress = r.get(f"doc_progress_{doc_id}")
            current_meta = None
            start_seg = 0
            if saved_progress:
                try:
                    p_data = json.loads(saved_progress)
                    current_meta = p_data.get("metadata")
                    start_seg = p_data.get("last_idx", -1) + 1
                    print(f"[*] Reluare procesare de la Segmentul {start_seg+1}...")
                except: pass

            # Ne asigurăm că LLM-ul este gata
            if not wait_for_llm():
                print(f"[!] LLM indisponibil. Amanare procesare document {doc_id}.")
                db.close(); time.sleep(10); continue

            # Execuție cu Re-încercare în caz de timeout/crash
            res = None
            for attempt in range(3):
                try:
                    res = extract_forensic_data(next_doc.raw_text, filename, doc_id, current_metadata=current_meta, start_segment=start_seg)
                    if res and res.get("is_finished"): break
                except Exception as e:
                    print(f"[!] Tentativa {attempt+1} esuata pentru {filename}: {e}")
                    time.sleep(10)

            if res and res.get("is_finished"):
                regex_transactions = extract_financial_regex(next_doc.raw_text)
                ai_transactions = res.get("metadata", {}).get("financial_data", [])
                
                # --- LOGICA DE IMPERECHERE 1-la-1 (Audit-Safe) ---
                final_financial = []
                used_ai_indices = set()
                
                for r_item in regex_transactions:
                    r_suma = float(r_item.get("suma", 0))
                    r_desc = r_item.get("descriere", "")
                    
                    found_match = False
                    for idx, a_item in enumerate(ai_transactions):
                        if idx in used_ai_indices: continue
                        
                        a_suma = float(a_item.get("suma", 0))
                        if abs(r_suma - a_suma) < 0.01:
                            if are_descriptions_similar(r_desc, a_item.get("descriere", "")):
                                r_item["descriere"] = a_item.get("descriere", r_desc)
                                used_ai_indices.add(idx)
                                found_match = True
                                break
                    
                    final_financial.append(r_item)
                
                for idx, a_item in enumerate(ai_transactions):
                    if idx not in used_ai_indices:
                        final_financial.append(a_item)

                db.query(models.FinancialItem).filter(models.FinancialItem.document_id == doc_id).delete()
                for item in final_financial:
                    try:
                        db.add(models.FinancialItem(
                            document_id=doc_id, description=item.get("descriere", "Tranzactie"),
                            amount=float(item.get("suma", 0)), currency=item.get("valuta", "RON"), doc_filename=filename
                        ))
                    except: pass
                
                next_doc.doc_type = res.get("doc_type")
                next_doc.doc_metadata = res.get("metadata")
                next_doc.ai_summary = res.get("summary")
                next_doc.status = "COMPLETED"
                
                # --- SINCRONIZARE MASTER ENTITIES (POSTGRES) ---
                try:
                    entitati = res.get("graph_data", {}).get("entitati", [])
                    for ent in entitati:
                        val = ent.get("valoare")
                        tip = ent.get("tip_entitate", "FIRMA")
                        if not val: continue
                        
                        m_ent = db.query(models.MasterEntity).filter(models.MasterEntity.official_name == val).first()
                        if not m_ent:
                            m_ent = models.MasterEntity(official_name=val, entity_type=tip)
                            db.add(m_ent)
                            db.flush()
                        
                        link = db.query(models.DocumentEntityLink).filter(
                            models.DocumentEntityLink.document_id == doc_id,
                            models.DocumentEntityLink.entity_id == m_ent.id
                        ).first()
                        if not link:
                            db.add(models.DocumentEntityLink(document_id=doc_id, entity_id=m_ent.id, role=ent.get("rol")))
                except Exception as e_sql:
                    print(f"[!] Eroare salvare Master Entities: {e_sql}")

                # --- SINCRONIZARE GRAF (NEO4J) ---
                try: 
                    case_obj = db.query(models.Case).filter(models.Case.id == next_doc.case_id).first()
                    m_id = case_obj.master_id if case_obj else None
                    graph_service.sync_document_to_graph(doc_id, filename, next_doc.case_id, res, master_id=m_id)
                except: pass
                
                db.commit()
                print(f"[+] Document {doc_id} FINALIZAT REZILIENT.")

        except Exception as e:
            print(f"[-] Eroare Worker: {e}"); db.rollback()
            if next_doc:
                time.sleep(5)
        finally:
            db.close()
        
        time.sleep(2)

if __name__ == "__main__":
    worker_loop()
