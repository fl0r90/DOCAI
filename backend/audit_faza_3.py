
import sys
import json
import os
sys.path.append('/app')
from core_engine.services.chat_service import query_investigator
from core_engine.database import SessionLocal
from core_engine.models import Document

def audit_retrieval_quality():
    print("=== AUDIT FAZA 3: CALITATE RAG ===")
    with SessionLocal() as db:
        doc = db.query(Document).filter(Document.filename == 'extras de cont.pdf').first()
        if not doc:
            print("Documentul extras de cont.pdf nu a fost gasit.")
            return
        
        case_id = doc.case_id
        # Testam intrebari specifice pe extrasul de cont
        queries = [
            "Exista tranzactii de 10500 lei? Explica cine le-a trimis.",
            "Care este suma primita de la Ros Mihaela?"
        ]
        
        for q in queries:
            print(f"\n[QUERY]: {q}")
            try:
                result = query_investigator(case_id, q)
                print(f"[ANSWER]: {result['answer']}")
                print(f"[CITATIONS]: {len(result['citations'])} surse citate.")
            except Exception as e:
                print(f"[ERROR]: {e}")

if __name__ == "__main__":
    audit_retrieval_quality()
