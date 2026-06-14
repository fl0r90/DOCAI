import json
import sys
import os
import uuid

# Adaugam backend-ul in path
sys.path.append("/app")

from core_engine.database import ForensicSessionLocal
from core_engine import models
from core_engine.services.graph_service import GraphService

def sync():
    with open("/app/audit_result_turbo.json", "r") as f:
        res = json.load(f)

    doc_id = 777
    filename = "extras de cont.pdf"
    
    db = ForensicSessionLocal()
    try:
        # 1. Documentul
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if not doc:
            doc = models.Document(id=doc_id, filename=filename, status="COMPLETED")
            db.add(doc)
            db.flush()

        # 2. Curatare tranzactii vechi
        db.query(models.FinancialItem).filter(models.FinancialItem.document_id == doc_id).delete()
        
        # 3. Ingestie tranzactii noi
        for item in res["metadata"]["financial_data"]:
            f_item = models.FinancialItem(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                transaction_date=str(item.get("data")),
                description=str(item.get("descriere")),
                amount=float(item.get("suma") or 0),
                currency=str(item.get("valuta") or "RON"),
                doc_filename=filename
            )
            db.add(f_item)
        
        db.commit()
        print(f"[*] Postgres: {len(res['metadata']['financial_data'])} tranzactii salvate.")
        
        # 4. Neo4j
        gs = GraphService()
        try:
            gs.sync_document_to_graph(doc_id, filename, 1, res["metadata"])
            print("[*] Neo4j: Sincronizare completa.")
        finally:
            gs.close()

    except Exception as e:
        print(f"[!] Eroare Sincronizare: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync()
