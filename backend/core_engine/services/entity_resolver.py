from sqlalchemy.orm import Session
from core_engine.models import Document, MasterEntity, DocumentEntityLink, FinancialItem, DocumentChunk
from core_engine.database import SessionLocal
import re

def save_entities_to_db(extracted_json: dict, doc_id: int = None):
    """
    Salvează datele extrase într-un mod ultra-robust, acceptând multiple variante de chei JSON.
    """
    if not extracted_json or not doc_id:
        print(f"[!] Date goale primite pentru salvare doc {doc_id}")
        return

    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc: return

        # 1. Metadate & Analiză (Robust)
        meta = extracted_json.get("metadata", {})
        if isinstance(meta, dict):
            doc.doc_type = meta.get("tip") or meta.get("tip_document")
            doc.doc_date = meta.get("data")
            doc.doc_number = meta.get("numar")
            try:
                val = meta.get("valoare") or meta.get("suma") or meta.get("valoare_totala")
                if val: doc.total_amount = float(val)
            except: pass

        analysis = extracted_json.get("analysis", {})
        if isinstance(analysis, dict):
            doc.ai_summary = analysis.get("summary")
            doc.risk_score = float(analysis.get("risk_score", 0.0))
            doc.risk_analysis = analysis.get("risk_explanation")

        # 2. Vector Chunks (Salvare în batch-uri)
        chunks = extracted_json.get("vector_chunks", [])
        if chunks:
            print(f"[*] Salvare {len(chunks)} vectori în batch-uri pentru doc {doc_id}...")
            for i in range(0, len(chunks), 10):
                batch = chunks[i:i+10]
                for chunk in batch:
                    new_chunk = DocumentChunk(
                        document_id=doc_id,
                        content=chunk["content"],
                        embedding=chunk["embedding"],
                        page_number=chunk.get("page")
                    )
                    db.add(new_chunk)
                db.commit() # Salvăm parțial
                print(f"[*] Batch {i//10 + 1} de vectori salvat.")

        # 3. Entități (Robust mapping)
        entitati = extracted_json.get("entitati", [])
        for e in entitati:
            # Încercăm toate variantele posibile de chei
            nume = e.get("nume") or e.get("full_legal_name") or e.get("name")
            if not nume or nume in ["...", "N/A", "Not specified"]: continue

            cui = e.get("cui") or e.get("cui_cif_cnp") or e.get("fiscal_id")
            rol = e.get("rol") or e.get("role") or e.get("rol_in_document")
            adresa = e.get("adresa") or e.get("full_address") or e.get("address")

            # Evităm duplicatele în master_entities
            exist = None
            if cui:
                exist = db.query(MasterEntity).filter(MasterEntity.cui_cif_cnp == str(cui)).first()
            if not exist:
                exist = db.query(MasterEntity).filter(MasterEntity.official_name == nume).first()
            
            if not exist:
                exist = MasterEntity(
                    official_name=nume,
                    cui_cif_cnp=str(cui) if cui else None,
                    entity_type="FIRMA" if cui else "PERSOANA",
                    address=adresa
                )
                db.add(exist)
                db.flush() # Pentru a genera ID-ul

            # Creăm legătura
            link = DocumentEntityLink(document_id=doc_id, entity_id=exist.id, role=rol)
            db.add(link)

        # 4. Itemi Financiari
        items = extracted_json.get("itemi_financiari", [])
        for it in items:
            desc = it.get("descriere") or it.get("description")
            if not desc or desc == "...": continue
            
            suma = it.get("suma") or it.get("amount") or it.get("suma_totala")
            new_it = FinancialItem(
                document_id=doc_id,
                description=desc,
                amount=float(suma) if suma else 0.0
            )
            db.add(new_it)

        db.commit()
        print(f"[+] Salvare completă pentru documentul {doc_id}!")

    except Exception as e:
        db.rollback()
        print(f"[!!!] Eroare critică la salvare doc {doc_id}: {e}")
    finally:
        db.close()
