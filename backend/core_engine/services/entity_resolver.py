from sqlalchemy.orm import Session
from core_engine.models import Document, MasterEntity, DocumentEntityLink, FinancialItem, DocumentChunk
from core_engine.database import SessionLocal
import re
import uuid

def normalize_entity_name(name: str) -> str:
    """Normalizează denumirile de firme pentru deduplicare robustă."""
    if not name: return ""
    name = str(name).upper()
    # Eliminăm prefixe/sufixe legale
    for token in [" S.R.L.", " SRL", " S.A.", " SA", " S.C. ", " SC ", " INC.", " LTD."]:
        name = name.replace(token, "")
    if name.startswith("SC "): name = name[3:]
    if name.startswith("S.C. "): name = name[5:]
    # Eliminăm caractere speciale și spații multiple
    name = re.sub(r'[^A-Z0-9]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

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
            tip = meta.get("tip") or meta.get("tip_document")
            if tip: doc.doc_type = tip
            data_val = meta.get("data") or meta.get("data_document")
            if data_val: doc.doc_date = str(data_val)
            nr_val = meta.get("numar") or meta.get("numar_document")
            if nr_val: doc.doc_number = str(nr_val)
            try:
                val = meta.get("valoare") or meta.get("suma") or meta.get("valoare_totala")
                if val: doc.total_amount = float(val)
            except: pass

        dyn_attrs = extracted_json.get("dynamic_attributes")
        if dyn_attrs and isinstance(dyn_attrs, dict):
            curr_meta = dict(doc.doc_metadata or {})
            curr_meta["dynamic_attributes"] = dyn_attrs
            doc.doc_metadata = curr_meta

        analysis = extracted_json.get("analysis", {})
        if isinstance(analysis, dict):
            if analysis.get("summary"):
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

        # 3. Entități (Robust mapping & Deduplicare inteligentă)
        entitati = extracted_json.get("entitati", [])
        for e in entitati:
            nume = e.get("nume") or e.get("full_legal_name") or e.get("name")
            if not nume or nume in ["...", "N/A", "Not specified"]: continue

            cui = e.get("cui") or e.get("cui_cif_cnp") or e.get("fiscal_id")
            rol = e.get("rol") or e.get("role") or e.get("rol_in_document")
            adresa = e.get("adresa") or e.get("full_address") or e.get("address")

            # Evităm duplicatele în master_entities folosind CUI și normalizarea numelui
            exist = None
            if cui:
                # 1. Căutare sigură după CUI
                exist = db.query(MasterEntity).filter(MasterEntity.cui_cif_cnp == str(cui)).first()
            
            if not exist:
                # 2. Căutare fuzzy după numele normalizat
                norm_name = normalize_entity_name(nume)
                if len(norm_name) > 3: # Nu căutăm firme cu 3 litere (prea multe false pozitive)
                    exist = db.query(MasterEntity).filter(MasterEntity.official_name.ilike(f"%{norm_name}%")).first()
                
                # 2b. LOGICĂ NOUĂ: Verificare permutări pentru persoane
                if not exist and len(norm_name.split()) == 2:
                    # Dacă numele are exact 2 cuvinte (Nume Prenume), încercăm să le inversăm
                    parts = norm_name.split()
                    reversed_name = f"{parts[1]} {parts[0]}"
                    exist = db.query(MasterEntity).filter(MasterEntity.official_name.ilike(f"%{reversed_name}%")).first()
            
            if not exist:
                # 3. Nu există în baza de date, cream una nouă
                exist = MasterEntity(
                    official_name=nume,
                    cui_cif_cnp=str(cui) if cui else None,
                    entity_type="FIRMA" if cui else "PERSOANA",
                    address=adresa
                )
                db.add(exist)
                db.flush() # Pentru a genera ID-ul

            # Creăm legătura cu documentul curent
            link = DocumentEntityLink(document_id=doc_id, entity_id=exist.id, role=rol)
            db.add(link)

        # 4. Itemi Financiari
        items = extracted_json.get("itemi_financiari", [])
        for it in items:
            desc = it.get("descriere") or it.get("description")
            if not desc or desc == "...": continue
            
            suma = it.get("suma") or it.get("amount") or it.get("suma_totala")
            new_it = FinancialItem(
                id=str(uuid.uuid4()),
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
