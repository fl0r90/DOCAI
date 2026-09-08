import time
import os
import redis
import json
import requests
import re
import uuid
import threading
import asyncio
from sqlalchemy import text
from contextlib import contextmanager
from core_engine.database import ForensicSessionLocal, engine
from core_engine import models
from core_engine.services.ocr_service import process_document
from core_engine.services.grinder import extract_forensic_data
from core_engine.services.graph_service import graph_service
from core_engine.services.storage_service import upsert_document_chunk

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

@contextmanager
def SafeSession():
    """Manager de context pentru sesiuni DB sigure în mediu multi-threaded."""
    session = ForensicSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def check_llm_pause():
    return r.exists("llm_active_session")

class EntityResolver:
    def __init__(self, db_session=None):
        self.noise_keywords = ['uber', 'bolt', 'glovo', 'lidl', 'kaufland', 'carrefour', 'mega image', 'omv', 'petrom', 'mol', 'profi', 'auchan', 'ikea', 'penny', 'magazin', 'farmacia', 'retea', 'tpark', 'google', 'youtube', 'emag', 'allianz', 'asigurare', 'eon', 'orange', 'vodafone', 'digi', 'enel']
        if db_session:
            try:
                config = db_session.execute(text("SELECT value FROM system_config WHERE key = 'noise_keywords'")).first()
                if config: self.noise_keywords = config[0]
            except: pass

    def is_noise(self, description):
        desc_lower = str(description).lower()
        return any(k in desc_lower for k in self.noise_keywords)

def extract_financial_regex(text_content):
    transactions = []
    lines = text_content.split('\n')
    date_pattern = r'\|\s*([0-9]{1,2})\s+([a-zA-ZăâîșțĂÂÎȘȚ]+)\s+(20[123][0-9])\s*\|'
    for line in lines:
        if '|' not in line: continue
        match = re.search(date_pattern, line, re.IGNORECASE)
        if not match: continue
        try:
            cells = [c.strip() for c in line.split('|')]
            if not cells[0]: cells.pop(0)
            if cells and not cells[-1]: cells.pop()
            if len(cells) < 4: continue
            zi, luna_nume, an = match.group(1).strip(), match.group(2).strip().lower(), match.group(3).strip()
            month_map = {'ianuarie': '01', 'februarie': '02', 'martie': '03', 'aprilie': '04', 'mai': '05', 'iunie': '06', 'iulie': '07', 'august': '08', 'septembrie': '09', 'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'}
            luna = month_map.get(luna_nume, "01")
            data_iso = f"{an}-{luna}-{zi.zfill(2)}"
            descriere = cells[1]
            debit_v = "".join(c for c in cells[2].replace(",", ".") if c.isdigit() or c == ".")
            credit_v = "".join(c for c in cells[3].replace(",", ".") if c.isdigit() or c == ".")
            val_d = float(debit_v) if debit_v else 0.0
            val_c = float(credit_v) if credit_v else 0.0
            t_type = "PLATA" if val_d > 0 else ("INCASARE" if val_c > 0 else "ALTA")
            final_val = val_d if t_type == "PLATA" else val_c
            if final_val > 0:
                transactions.append({"data": data_iso, "descriere": descriere, "suma": final_val, "valuta": "RON", "transaction_type": t_type, "raw_line": line})
        except: continue
    return transactions

def split_into_child_chunks(text, chunk_size=350, overlap=50):
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
        if start >= len(text) - overlap:
            break
    return chunks

def _create_chunks_and_embeddings(doc_id, chunks_data, filename="unknown"):
    if not chunks_data: return []
    print(f"[*] Procesare vectori Parent-Child pre-commit...")
    try: requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "mistral:latest", "keep_alive": 0}, timeout=5)
    except: pass
    inserted_ids = []
    with SafeSession() as db:
        db.execute(text("DELETE FROM document_chunks WHERE document_id = :id"), {"id": doc_id})
        parent_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{doc_id}")
        db.execute(text("DELETE FROM document_storage WHERE parent_doc_id = :p_id"), {"p_id": str(parent_uuid)})
        db.flush()
        
        child_idx = 0
        for idx, item in enumerate(chunks_data):
            content = (item.get("content") or item.get("text", "")) if isinstance(item, dict) else item
            page_no = item.get("page", 1) if isinstance(item, dict) else 1
            spatial = item.get("spatial", "") if isinstance(item, dict) else ""
            if not content or len(content.strip()) < 5: continue
            safe_content = "".join(c for c in content if c.isprintable() or c in "\n\r\t")
            
            # 1. Creăm și salvăm Parent Chunk (fără embedding)
            parent_chunk = models.DocumentChunk(
                document_id=doc_id,
                content=safe_content,
                page_number=page_no,
                spatial=spatial,
                embedding=None,
                parent_chunk_id=None
            )
            db.add(parent_chunk)
            db.flush()  # Generăm parent_chunk.id
            
            # 2. Spargem în Child Chunks și calculăm embeddings
            child_texts = split_into_child_chunks(safe_content, chunk_size=350, overlap=50)
            for c_text in child_texts:
                if len(c_text.strip()) < 5: continue
                success = False
                for attempt in range(2):
                    try:
                        res = requests.post(
                            f"{OLLAMA_URL}/api/embeddings", 
                            json={"model": "bge-m3", "prompt": c_text[:3500], "keep_alive": 300}, 
                            timeout=20
                        )
                        if res.status_code == 200:
                            embedding = res.json().get("embedding")
                            if embedding:
                                new_child = models.DocumentChunk(
                                    document_id=doc_id,
                                    content=c_text,
                                    page_number=page_no,
                                    spatial=spatial,
                                    embedding=embedding,
                                    parent_chunk_id=parent_chunk.id
                                )
                                db.add(new_child)
                                db.flush()
                                inserted_ids.append({"id": new_child.id, "content": c_text})
                                
                                # Upsert în document_storage
                                upsert_document_chunk(
                                    db, 
                                    {
                                        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"chunk_{doc_id}_{child_idx}")), 
                                        "parent_doc_id": str(parent_uuid), 
                                        "content": c_text, 
                                        "metadata": {"filename": filename, "page": page_no, "spatial": spatial, "parent_chunk_id": parent_chunk.id}
                                    }, 
                                    embedding
                                )
                                child_idx += 1
                                success = True
                                break
                    except Exception as e:
                        print(f"[!] Error creating embedding for child chunk: {e}")
                        time.sleep(1)
                
                if not success:
                    new_child = models.DocumentChunk(
                        document_id=doc_id,
                        content=c_text,
                        page_number=page_no,
                        spatial=spatial,
                        parent_chunk_id=parent_chunk.id
                    )
                    db.add(new_child)
                    db.flush()
                    inserted_ids.append({"id": new_child.id, "content": c_text})
                    
        db.commit()
    return inserted_ids

def unified_worker_pipeline():
    """Pipeline Liniar UNIFICAT v0.5.0 (Resource-Aware & LLM Extraction)"""
    print("!!! PIPELINE FORENSIC v0.5.0 - RESOURCE AWARE !!!")
    
    from core_engine.services.grinder import _unload_ollama
    import gc
    import torch
    
    while True:
        if check_llm_pause(): time.sleep(10); continue
        try:
            doc_id, filename = None, None
            with SafeSession() as db:
                next_doc = db.query(models.Document).filter(models.Document.status == "QUEUED").order_by(models.Document.created_at.asc()).first()
                if not next_doc: time.sleep(5); continue
                doc_id, filename = next_doc.id, next_doc.filename
                next_doc.status = "PROCESSING"; db.commit()
            
            print(f"[*] --- START: {filename} ---")
            with SafeSession() as db:
                next_doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
                resolver = EntityResolver(db_session=db)
                
                # 1. VRAM MARSHALLING (Eliberăm Ollama pentru Docling)
                r.set(f"doc_progress_{doc_id}", json.dumps({"status": "OCR", "percent": 10, "eta_seconds": 120, "message": "OCR structural (GPU)..."}))
                _unload_ollama()
                
                file_path = os.path.join("/app/uploads", filename)
                if not os.path.exists(file_path): file_path = os.path.join("/app/shared_uploads", filename)
                
                # 2. DOCLING OCR
                ocr_result = process_document(file_path)
                if not ocr_result or "error" in ocr_result: 
                    next_doc.status = "FAILED"; db.commit(); continue
                next_doc.raw_text = ocr_result.get("markdown", ""); db.commit()

                # 3. VRAM MARSHALLING (Eliberăm PyTorch pentru Ollama)
                gc.collect()
                if torch.cuda.is_available(): torch.cuda.empty_cache()

                # 4. EMBEDDINGS (pgvector)
                r.set(f"doc_progress_{doc_id}", json.dumps({"status": "RAG", "percent": 40, "eta_seconds": 60, "message": "Indexare Vectorială..."}))
                chunks_info = _create_chunks_and_embeddings(doc_id, ocr_result.get("chunks", []), filename=filename)
                
                # 5. STRUCTURED EXTRACTION (Grinder - LLM JSON Mode)
                # Stergem datele vechi financiare in caz de re-procesare
                db.query(models.FinancialItem).filter(models.FinancialItem.document_id == doc_id).delete()
                db.commit()

                r.set(f"doc_progress_{doc_id}", json.dumps({"status": "AI_GRINDER", "percent": 60, "eta_seconds": 300, "message": "Audit Cifre & Entități (LLM)..."}))
                res = asyncio.run(extract_forensic_data(ocr_result, filename, doc_id))
                
                # 6. GRAPH SYNC & FINAL SYNTHESIS
                if res and res.get("is_finished"):
                    ai_data = res.get("metadata", {})
                    
                    # ENRICHMENT: Mapăm entitățile AI pe MasterEntities din SQL
                    graph_data = ai_data.get("graph_data", {"entitati": [], "relatii": []})
                    for ent in graph_data.get("entitati", []):
                        val = ent.get("valoare")
                        tip = ent.get("tip_entitate")
                        
                        # Căutăm în SQL dacă avem deja entitatea asta „curată”
                        m_ent = None
                        if tip in ["CUI", "FIRMA"]:
                            m_ent = db.query(models.MasterEntity).filter(
                                (models.MasterEntity.cui_cif_cnp == val) | 
                                (models.MasterEntity.official_name == val)
                            ).first()
                        
                        if m_ent:
                            ent["master_entity_id"] = m_ent.id
                            ent["official_name"] = m_ent.official_name
                        else:
                            # Opțional: Dacă e o entitate nouă importantă, o putem crea aici în Master
                            if tip in ["CUI", "FIRMA"] and len(val) > 3:
                                try:
                                    new_m = models.MasterEntity(official_name=val, cui_cif_cnp=val if tip == "CUI" else None)
                                    db.add(new_m); db.commit(); db.refresh(new_m)
                                    ent["master_entity_id"] = new_m.id
                                except: db.rollback()

                    # GENERARE SINTEZA REALA CU LLM
                    from core_engine.services.llm_service import LLMService
                    from core_engine.core.config import get_llm_config
                    llm_synth = LLMService()
                    synth_prompt = f"### System:\nEști un Auditor Forensic. Generează un REZUMAT EXECUTIV (Sinteză) în limba ROMÂNĂ pentru documentul '{filename}'. Concentrează-te pe scopul documentului, entitățile principale și datele cheie identified. Fii scurt și precis.\n### User:\n{next_doc.raw_text[:8000]}\n"
                    
                    print(f"[*] Generăm sinteza documentului...")
                    try:
                        cfg = get_llm_config()
                        narrative_model = cfg.get("specialist_narrative") or cfg.get("active_model") or "gemma4:e4b"
                        summary_text = asyncio.run(llm_synth.generate(synth_prompt, narrative_model, is_json=False))
                        next_doc.ai_summary = summary_text
                    except Exception as e:
                        print(f"[!] Eroare la generarea sintezei: {e}")
                        next_doc.ai_summary = "Document procesat, dar sinteza automată a eșuat."
                    
                    # Salvăm metadatele finale (inclusiv entitățile îmbogățite)
                    next_doc.doc_metadata = {
                        "financial_data": ai_data.get("financial_data", []), 
                        "outline": ocr_result.get("outline", []),
                        "graph_data": graph_data
                    }
                    
                    case_obj = db.query(models.Case).filter(models.Case.id == next_doc.case_id).first()
                    graph_service.sync_document_to_graph(
                        doc_id, 
                        filename, 
                        next_doc.case_id, 
                        next_doc.doc_metadata, 
                        master_id=case_obj.master_id if case_obj else None
                    )
                
                next_doc.status = "COMPLETED"; db.commit()
                r.set(f"doc_progress_{doc_id}", json.dumps({"status": "COMPLETED", "percent": 100, "message": "Succes."}))
        except Exception as e: 
            print(f"[!] Eroare Worker Pipeline: {e}")
            time.sleep(5)
if __name__ == "__main__":
    unified_worker_pipeline()
