
import re
import sys
import os

# Adaugam folderul curent la path
sys.path.append('/app')

from core_engine.database import SessionLocal
from core_engine.models import Document, DocumentChunk
from sqlalchemy import or_, and_, text as sql_text

def simulate_agent_search(case_id, user_question):
    print(f"--- SIMULARE CAUTARE AGENT (NOUA LOGICA) ---")
    print(f"Intrebare: {user_question}")
    
    with SessionLocal() as db:
        doc_ids = [d.id for d in db.query(Document).filter(Document.case_id == case_id).all()]
        print(f"Documente in caz: {doc_ids}")
        
        # NOUA LOGICA: [A-Z]{3,30}|\d+[\.,]\d{2}|\d{4,}
        anchors = re.findall(r'[A-Z]{3,30}|\d+[\.,]\d{2}|\d{4,}', user_question)
        print(f"Ancore identificate: {anchors}")
        
        all_chunks = []
        financial_evidence = ""
        
        if anchors:
            # 1. Căutare în fragmente
            cond = and_(DocumentChunk.document_id.in_(doc_ids), or_(*[DocumentChunk.content.ilike(f"%{a}%") for a in anchors]))
            all_chunks = db.query(DocumentChunk).filter(cond).limit(15).all()
            print(f"Fragmente gasite prin ancore: {len(all_chunks)}")

            # 2. Căutare financiară (SQL)
            try:
                for a in anchors:
                    if a.isdigit() or ('.' in a or ',' in a):
                        clean_val = a.replace('.', '').replace(',', '.')
                        if clean_val.count('.') > 1: clean_val = clean_val.replace('.', '', clean_val.count('.') - 1)
                        try:
                            amount_val = float(clean_val)
                            sql = sql_text("SELECT transaction_date, description, amount, currency, doc_filename FROM financial_items WHERE document_id = ANY(:ids) AND (amount = :val OR amount = -:val)")
                            res = db.execute(sql, {"ids": doc_ids, "val": amount_val}).fetchall()
                            for r in res:
                                financial_evidence += f"[TRANZACȚIE CERTIFICATĂ]: Data: {r[0]} | Suma: {r[2]} {r[3]} | Descriere: {r[1]} (Sursa: {r[4]})\n"
                        except: pass
            except Exception as e:
                print(f"Error in financial search: {e}")

        if not all_chunks and not financial_evidence:
            print("Fallback pe cuvinte...")
            # ... (logica fallback ramane la fel)

        if financial_evidence:
            print(f"\nEVIDENTA FINANCIARA GASITA:\n{financial_evidence}")

        for r in all_chunks:
            print(f"\n[Source {r.document_id}, Page {r.page_number}, ID {r.id}]:")
            # CONTEXT COMPLET (fara trunchiere la 300)
            clean_content = re.sub(r'> \[CONTEXT:.*?\]|> \[SPAȚIAL:.*?\]|={5,}', '', r.content).strip()
            print(clean_content[:500] + "...")

# Gasim documentul 135
with SessionLocal() as db:
    doc = db.query(Document).filter(Document.id == 135).first()
    if doc:
        simulate_agent_search(doc.case_id, "Cine a trimis 10500 lei?")
