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
from core_engine.services.toc import toc_service
from core_engine.services.debug_logger import debug_logger

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
                config = db_session.execute(text("SELECT value FROM system_settings WHERE key = 'noise_keywords'")).first()
                if config: self.noise_keywords = config[0]
            except Exception:
                db_session.rollback()

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

from core_engine.services.chunker_service import semantic_chunker

def _create_chunks_and_embeddings(doc_id, chunks_data, filename="unknown", raw_markdown=None, tracker=None):
    if not chunks_data and not raw_markdown:
        return []
    print(f"[*] Semantic Parent-Child Vector Indexing for doc {doc_id} ({filename})...")
    try:
        requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "mistral:latest", "keep_alive": 0}, timeout=5)
    except Exception:
        pass
        
    inserted_ids = []
    
    # Extract markdown if passed in chunks_data dict
    chunks_list = []
    if isinstance(chunks_data, dict):
        raw_markdown = raw_markdown or chunks_data.get("markdown")
        chunks_list = chunks_data.get("chunks", [])
    elif isinstance(chunks_data, list):
        chunks_list = chunks_data

    # Generate semantic chunks
    if raw_markdown and len(raw_markdown.strip()) > 10:
        semantic_chunks = semantic_chunker.chunk_markdown(raw_markdown, filename=filename)
        # Assign correct page numbers using position-based matching
        if chunks_list:
            pos_pages = []
            for item in chunks_list:
                if isinstance(item, dict):
                    c = (item.get("content") or "").strip()
                    p = item.get("page", 1)
                    if c and len(c) > 10:
                        idx = raw_markdown.find(c[:50])
                        if idx != -1:
                            pos_pages.append((idx, p))
            pos_pages.sort(key=lambda x: x[0])
            if pos_pages:
                for sc in semantic_chunks:
                    chunk_content = sc.get("content", "")
                    clean = re.sub(r'^\[Doc:[^\]]*\]\s*', '', chunk_content).strip()
                    if not clean:
                        continue
                    search = clean[:80].strip()
                    if not search:
                        continue
                    idx = raw_markdown.find(search)
                    if idx == -1:
                        search = clean[:40].strip()
                        idx = raw_markdown.find(search)
                    if idx == -1:
                        continue
                    page = 1
                    for pos, p in pos_pages:
                        if pos <= idx:
                            page = p
                        else:
                            break
                    sc["page_number"] = page
    else:
        # Fallback if no raw markdown is present
        semantic_chunks = []
        for item in chunks_list:
            content = (item.get("content") or item.get("text", "")) if isinstance(item, dict) else item
            page_no = item.get("page", 1) if isinstance(item, dict) else 1
            spatial = item.get("spatial", "") if isinstance(item, dict) else ""
            if not content or len(content.strip()) < 5:
                continue
            if semantic_chunker.is_table_block(content):
                tbl_chunks = semantic_chunker.chunk_table(content, context_header=f"[Doc: {filename}]")
                for tc in tbl_chunks:
                    semantic_chunks.append({
                        "content": tc,
                        "parent_content": content,
                        "is_table": True,
                        "page_number": page_no,
                        "spatial": spatial
                    })
            else:
                txt_chunks = semantic_chunker.split_narrative(content, context_header=f"[Doc: {filename}]")
                for tc in txt_chunks:
                    semantic_chunks.append({
                        "content": tc,
                        "parent_content": content,
                        "is_table": False,
                        "page_number": page_no,
                        "spatial": spatial
                    })

    if not semantic_chunks:
        return []

    with SafeSession() as db:
        db.execute(text("DELETE FROM document_chunks WHERE document_id = :id"), {"id": doc_id})
        parent_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{doc_id}")
        db.execute(text("DELETE FROM document_storage WHERE parent_doc_id = :p_id"), {"p_id": str(parent_uuid)})
        db.flush()

        child_idx = 0
        from collections import OrderedDict
        parent_groups = OrderedDict()
        for c in semantic_chunks:
            p_content = c.get("parent_content") or c["content"]
            if p_content not in parent_groups:
                parent_groups[p_content] = []
            parent_groups[p_content].append(c)

        total_children = sum(len(ch_list) for ch_list in parent_groups.values())
        if tracker:
            tracker.start_rag_phase(total_children)

        processed_children = 0
        for p_content, children in parent_groups.items():
            safe_parent = "".join(ch for ch in p_content if ch.isprintable() or ch in "\n\r\t")
            first_child = children[0]
            page_no = first_child.get("page_number", 1)
            spatial = first_child.get("spatial", "")

            # 1. Save Parent Chunk (embedding=None)
            parent_chunk = models.DocumentChunk(
                document_id=doc_id,
                content=safe_parent,
                page_number=page_no,
                spatial=spatial,
                embedding=None,
                parent_chunk_id=None
            )
            db.add(parent_chunk)
            db.flush()

            # 2. Save Child Chunks with embeddings
            for child in children:
                processed_children += 1
                child_content = child["content"]
                safe_child = "".join(ch for ch in child_content if ch.isprintable() or ch in "\n\r\t")
                if len(safe_child.strip()) < 5:
                    if tracker:
                        tracker.update_rag_chunk(processed_children)
                    continue

                success = False
                for attempt in range(2):
                    try:
                        from core_engine.services.embedding_service import EmbeddingService
                        embedding = EmbeddingService.get_embedding(safe_child[:3500])
                        if embedding:
                            new_child = models.DocumentChunk(
                                document_id=doc_id,
                                content=safe_child,
                                page_number=page_no,
                                spatial=spatial,
                                embedding=embedding,
                                parent_chunk_id=parent_chunk.id
                            )
                            db.add(new_child)
                            db.flush()
                            inserted_ids.append({"id": new_child.id, "content": safe_child})

                            # Upsert in document_storage
                            upsert_document_chunk(
                                db,
                                {
                                    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"chunk_{doc_id}_{child_idx}")),
                                    "parent_doc_id": str(parent_uuid),
                                    "content": safe_child,
                                    "metadata": {
                                        "filename": filename,
                                        "page": page_no,
                                        "spatial": spatial,
                                        "parent_chunk_id": parent_chunk.id,
                                        "is_table": child.get("is_table", False)
                                    }
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
                        content=safe_child,
                        page_number=page_no,
                        spatial=spatial,
                        parent_chunk_id=parent_chunk.id
                    )
                    db.add(new_child)
                    db.flush()
                    inserted_ids.append({"id": new_child.id, "content": safe_child})

                if tracker:
                    tracker.update_rag_chunk(processed_children)

        db.commit()
        if tracker:
            tracker.finish_rag_phase()
    print(f"[+] Successfully indexed {len(inserted_ids)} child chunks under {len(parent_groups)} parent chunks for doc {doc_id}.")
    return inserted_ids

def unified_worker_pipeline():
    """Pipeline Liniar UNIFICAT v0.7.0 (Resource-Aware, Distributed & Multi-Node)"""
    worker_id = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:6]}")
    print(f"!!! PIPELINE FORENSIC v0.7.0 - DISTRIBUTED WORKER [{worker_id}] !!!")
    
    from core_engine.services.grinder import _unload_ollama
    import gc
    import torch
    
    while True:
        r.set(f"worker_heartbeat_{worker_id}", json.dumps({
            "worker_id": worker_id,
            "timestamp": int(time.time()),
            "status": "IDLE"
        }), ex=60)

        if check_llm_pause(): time.sleep(10); continue
        try:
            doc_id, filename = None, None
            with SafeSession() as db:
                next_doc = db.query(models.Document).filter(models.Document.status == "QUEUED").order_by(models.Document.created_at.asc()).first()
                if not next_doc: time.sleep(5); continue
                doc_id, filename = next_doc.id, next_doc.filename
                next_doc.status = "PROCESSING"; db.commit()
            
            r.set(f"worker_heartbeat_{worker_id}", json.dumps({
                "worker_id": worker_id,
                "timestamp": int(time.time()),
                "status": "PROCESSING",
                "current_doc": filename
            }), ex=60)
            print(f"[*] --- START [{worker_id}]: {filename} ---")
            file_path = os.path.join("/app/uploads", filename)
            if not os.path.exists(file_path): file_path = os.path.join("/app/shared_uploads", filename)

            from core_engine.services.progress_tracker import DocProgressTracker
            tracker = DocProgressTracker(doc_id, filename, file_path, redis_client=r)

            with SafeSession() as db:
                next_doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
                resolver = EntityResolver(db_session=db)
                debug_logger.task_stage(doc_id=doc_id, stage="PIPELINE_START", status="STARTED", details={"filename": filename, "worker_id": worker_id})
                
                # 1. VRAM MARSHALLING (Eliberăm Ollama pentru Docling)
                tracker.start_ocr_phase()
                _unload_ollama()
                
                # 2. DOCLING OCR
                ocr_result = process_document(file_path)
                if not ocr_result or "error" in ocr_result: 
                    tracker.fail("OCR structural a eșuat.")
                    debug_logger.task_stage(doc_id=doc_id, stage="OCR", status="FAILED", details={"error": ocr_result.get("error") if isinstance(ocr_result, dict) else "unknown"})
                    next_doc.status = "FAILED"; db.commit(); continue
                
                items = ocr_result.get("items", []) if isinstance(ocr_result, dict) else []
                num_tables = len([it for it in items if it.get("type") in ["TABLE", "TABLE_PART"]])
                tracker.finish_ocr_phase(num_tables=num_tables)
                debug_logger.task_stage(doc_id=doc_id, stage="OCR", status="COMPLETED", details={"tables_count": num_tables})

                next_doc.raw_text = ocr_result.get("markdown", ""); db.commit()

                # 3. VRAM MARSHALLING (Eliberăm PyTorch pentru Ollama)
                gc.collect()
                if torch.cuda.is_available(): torch.cuda.empty_cache()

                # 4. EMBEDDINGS (pgvector)
                chunks_info = _create_chunks_and_embeddings(doc_id, ocr_result, filename=filename, raw_markdown=ocr_result.get("markdown", ""), tracker=tracker)
                debug_logger.task_stage(doc_id=doc_id, stage="EMBEDDINGS", status="COMPLETED", details={"chunks_count": len(chunks_info)})
                
                # 5. STRUCTURED EXTRACTION (Universal Deep Forensic AI Audit Engine)
                tracker.start_grinder_overview(total_tables=num_tables)
                from core_engine.services.deep_audit_service import DeepForensicAuditor
                auditor = DeepForensicAuditor(doc_id)
                audit_res = asyncio.run(auditor.run_audit())
                tracker.finish_grinder_overview()

                ents_found = audit_res.get("entities_count", 0)
                has_summary = bool(audit_res.get("summary_length", 0) > 50)
                debug_logger.task_stage(doc_id=doc_id, stage="GRINDER_EXTRACTION", status="COMPLETED", details={"entities_count": ents_found, "has_summary": has_summary, "financial_items": audit_res.get("financial_items_count", 0)})

                next_doc.status = "COMPLETED"
                db.commit()
                tracker.complete()
                pipe_status = "SUCCESS" if (ents_found > 0 or has_summary) else "COMPLETED_WITH_WARNINGS"
                debug_logger.task_stage(doc_id=doc_id, stage="PIPELINE_END", status=pipe_status, details={"filename": filename, "entities_count": ents_found, "has_summary": has_summary})

        except Exception as e: 
            if 'tracker' in locals() and tracker:
                tracker.fail(str(e))
            print(f"[!] Eroare Worker Pipeline: {e}")
            debug_logger.error("worker_tasks", "PIPELINE_FAILED", str(e), doc_id=doc_id if 'doc_id' in locals() else None, details={"filename": filename if 'filename' in locals() else None})
            time.sleep(5)
if __name__ == "__main__":
    unified_worker_pipeline()
