
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append("/app")

from core_engine.database import SessionLocal
from core_engine.models import Document, FinancialItem
from core_engine.services.grinder import extract_forensic_data

def force_reprocess_invoice(doc_id):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            print(f"Doc {doc_id} not found")
            return
            
        print(f"[*] Reprocessing {doc.filename}...")
        
        # Read full text
        full_text = doc.raw_text if hasattr(doc, 'raw_text') and doc.raw_text else ""
        if not full_text:
            # Try to reconstruct from chunks if raw_text is missing
            from core_engine.models import DocumentChunk
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.id).all()
            full_text = "\n".join([c.content for c in chunks])
            
        if not full_text:
            print("No text found for document")
            return
            
        res = extract_forensic_data(full_text, doc.filename, doc.id)
        
        print(f"[*] Extraction finished. Found {len(res.get('financial_data', []))} transactions.")
        
        # Save to DB
        for item in res.get('financial_data', []):
            import uuid
            new_item = FinancialItem(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                doc_number=res.get("metadata", {}).get("data_document", ""),
                doc_filename=doc.filename,
                transaction_date=item.get("data"),
                description=item.get("descriere"),
                amount=float(item.get("suma", 0)),
                currency=item.get("valuta", "RON"),
                doc_type=res.get("doc_type"),
                transaction_type="FACTURARE" if res.get("doc_type") == "FACTURA" else "TRANZACTIE",
                cui_source=item.get("cui_sursa"),
                iban_source=item.get("iban_sursa"),
                cui_destination=item.get("cui_destinatie"),
                iban_destination=item.get("iban_destinatie")
            )
            db.add(new_item)
        
        db.commit()
        print("[+] Success.")
        
    finally:
        db.close()

if __name__ == "__main__":
    force_reprocess_invoice(130)
