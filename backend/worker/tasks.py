import time
import os
import redis
import json
from sqlalchemy import desc
from app.database import ForensicSessionLocal
from app import models
from app.services.ocr_service import process_document
from app.services.grinder import extract_forensic_data
from app.services.graph_service import graph_service

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)

def check_llm_pause():
    return r.exists("llm_active_session")

def worker_loop():
    print("[*] Grinder 2.0 pornit cu suport Resume & VRAM Marshalling (Fixed).")
    
    while True:
        if check_llm_pause():
            time.sleep(10)
            continue

        db = ForensicSessionLocal()
        next_doc = None
        try:
            next_doc = db.query(models.Document).filter(models.Document.status.in_(["QUEUED", "AI_EXTRACTING"]))\
                .order_by(models.Document.created_at.asc())\
                .first()

            if not next_doc:
                db.close(); time.sleep(5); continue

            doc_id = next_doc.id
            filename = next_doc.filename
            
            # Pas 1: OCR (doar dacă e la început)
            if next_doc.status == "QUEUED":
                next_doc.status = "OCR_PROCESSING"; db.commit()
                file_path = os.path.join("/app/uploads", filename)
                if not os.path.exists(file_path): file_path = os.path.join("/app/backend/uploads", filename)
                text_content = process_document(file_path)
                next_doc.raw_text = text_content
                next_doc.status = "AI_EXTRACTING"; db.commit()
            
            # Pas 2: Reluare din Redis sau Start Nou
            progress_raw = r.get(f"doc_progress_{doc_id}")
            start_idx = 0
            current_meta = next_doc.doc_metadata
            
            if progress_raw:
                p_data = json.loads(progress_raw)
                start_idx = p_data["last_idx"] + 1
                current_meta = p_data["metadata"]
                print(f"[*] Reluare document {doc_id} de la segmentul {start_idx}")

            # Analiză AI cu 5 argumente
            res = extract_forensic_data(next_doc.raw_text, filename, doc_id, current_meta, start_idx)
            
            db.expire_all()
            curr_doc = db.query(models.Document).filter(models.Document.id == doc_id).first()

            if res.get("is_finished"):
                curr_doc.doc_type = res.get("doc_type")
                curr_doc.doc_metadata = res.get("metadata")
                curr_doc.ai_summary = res.get("summary")
                curr_doc.issue_date = res.get("metadata", {}).get("data_document")
                curr_doc.status = "COMPLETED"
                try:
                    graph_service.sync_document_to_graph(doc_id, filename, curr_doc.case_id, res, curr_doc.case.master_id if curr_doc.case else None)
                except Exception as ge: print(f"Graph Error: {ge}")
                print(f"[+] Document {doc_id} FINALIZAT.")
            else:
                curr_doc.doc_metadata = res.get("metadata")
                curr_doc.processing_progress = res.get("next_segment")
                print(f"[!] Document {doc_id} PAUZAT la segmentul {res.get('next_segment')}")

            db.commit()

        except Exception as e:
            print(f"[-] Eroare: {e}"); db.rollback()
            if next_doc:
                try:
                    with ForensicSessionLocal() as err_db:
                        err_doc = err_db.query(models.Document).filter(models.Document.id == doc_id).first()
                        if err_doc: err_doc.status = "ERROR"; err_db.commit()
                except: pass
        finally:
            db.close()
        
        time.sleep(2)

if __name__ == "__main__":
    worker_loop()
