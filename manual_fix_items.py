import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Connect to DB
FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def extract_financial_regex(text_content):
    """Extracție robustă a tranzacțiilor suportând multiple formate de tabele."""
    transactions = []
    month_map = {
        'ianuarie': '01', 'februarie': '02', 'martie': '03', 'aprilie': '04',
        'mai': '05', 'iunie': '06', 'iulie': '07', 'august': '08',
        'septembrie': '09', 'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
    }
    
    pattern = r'\|\s*([0-9]{2})\s+([a-zăâîșț]+)\s+(202[0-9])\s*\|(.*)'
    matches = re.finditer(pattern, text_content, re.IGNORECASE)
    
    for match in matches:
        try:
            zi = match.group(1).strip()
            luna_nume = match.group(2).strip().lower()
            an = match.group(3).strip()
            rest = match.group(4)
            
            luna = month_map.get(luna_nume, "01")
            data_iso = f"{an}-{luna}-{zi}"
            
            cols = [c.strip() for c in rest.split('|')]
            if cols and not cols[-1]: cols.pop()
            
            if not cols: continue
            desc = cols[0]
            amounts = []
            for c in cols:
                clean = "".join(ch for ch in c.replace(',', '.') if ch.isdigit() or ch == '.')
                try:
                    if clean: amounts.append(float(clean))
                    else: amounts.append(None)
                except: amounts.append(None)
            
            suma = 0
            final_desc = desc
            if len(cols) >= 3:
                credit = amounts[-2] if len(amounts) >= 2 else None
                debit = amounts[-3] if len(amounts) >= 3 else (amounts[-2] if len(amounts) >= 2 else None)
                if len(amounts) >= 3 and amounts[-2] is not None and amounts[-2] > 0:
                    suma = amounts[-2]
                    final_desc = f"INCASARE: {desc}"
                elif len(amounts) >= 3 and amounts[-3] is not None and amounts[-3] > 0:
                    suma = amounts[-3]
                    final_desc = f"PLATA: {desc}"
                else:
                    for a_idx, val in enumerate(reversed(amounts)):
                        if val is not None and val > 0:
                            suma = val
                            final_desc = f"TRANZACTIE: {desc}"
                            break

            if suma > 0:
                transactions.append({"data": data_iso, "descriere": final_desc, "suma": suma})
        except: continue
    return transactions

def fix_doc(doc_id):
    db = SessionLocal()
    try:
        doc = db.execute(text("SELECT raw_text, filename FROM documents WHERE id = :id"), {"id": doc_id}).fetchone()
        if not doc or not doc[0]: return
        
        items = extract_financial_regex(doc[0])
        print(f"Extracted {len(items)} items for doc {doc_id} ({doc[1]})")
        
        db.execute(text("DELETE FROM financial_items WHERE document_id = :id"), {"id": doc_id})
        for item in items:
            db.execute(text("""
                INSERT INTO financial_items (document_id, description, amount, currency, transaction_date, doc_filename)
                VALUES (:doc_id, :desc, :amount, 'RON', :date, :filename)
            """), {
                "doc_id": doc_id, "desc": item["descriere"], "amount": item["suma"], 
                "date": item["data"], "filename": doc[1]
            })
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    fix_doc(129)
    fix_doc(130)
