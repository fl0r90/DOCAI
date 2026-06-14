import re
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Database Connection
FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_all_transactions(doc_id):
    db = SessionLocal()
    try:
        # 1. Get RAW OCR text
        doc = db.execute(text("SELECT raw_text FROM documents WHERE id = :id"), {"id": doc_id}).fetchone()
        if not doc or not doc[0]:
            print("Error: No OCR text found.")
            return
        raw_text = doc[0]

        # 2. Get DB transactions
        db_items = db.execute(text("SELECT transaction_date, amount, description FROM financial_items WHERE document_id = :id"), {"id": doc_id}).fetchall()
        
        # 3. Extract OCR transactions (using the same robust logic as the worker)
        ocr_lines = []
        pattern = r'\|\s*([0-9]{2})\s+([a-zăâîșț]+)\s+(202[0-9])\s*\|(.*)'
        matches = re.finditer(pattern, raw_text, re.IGNORECASE)
        
        month_map = {
            'ianuarie': '01', 'februarie': '02', 'martie': '03', 'aprilie': '04',
            'mai': '05', 'iunie': '06', 'iulie': '07', 'august': '08',
            'septembrie': '09', 'octombrie': '10', 'noiembrie': '11', 'decembrie': '12'
        }

        for match in matches:
            zi, luna_nume, an, rest = match.group(1), match.group(2).lower(), match.group(3), match.group(4)
            data_iso = f"{an}-{month_map.get(luna_nume, '01')}-{zi}"
            
            cols = [c.strip() for c in rest.split('|')]
            if cols and not cols[-1]: cols.pop()
            
            amounts = []
            for c in cols:
                clean = "".join(ch for ch in c.replace(',', '.') if ch.isdigit() or ch == '.')
                try: amounts.append(float(clean))
                except: amounts.append(None)
            
            # Simple check for any amount in the line
            for a in amounts:
                if a and a > 0:
                    ocr_lines.append({"date": data_iso, "amount": a, "desc": cols[0]})
                    break

        print(f"--- VERIFICARE INTEGRALĂ DOC {doc_id} ---")
        print(f"Tranzacții detectate în OCR (brut): {len(ocr_lines)}")
        print(f"Tranzacții salvate în SQL: {len(db_items)}")
        
        # 4. Matching Logic
        matches_found = 0
        hallucinations = []
        
        for db_item in db_items:
            db_date, db_amount, db_desc = db_item
            # Find in OCR
            found = False
            for ocr in ocr_lines:
                # Match by date and amount (descriptions might have prefixes)
                if ocr["date"] == db_date and abs(ocr["amount"] - db_amount) < 0.01:
                    matches_found += 1
                    found = True
                    ocr_lines.remove(ocr) # Remove to avoid double counting
                    break
            if not found:
                hallucinations.append(db_item)

        print(f"Potriviri exacte (OCR <-> SQL): {matches_found}")
        
        if hallucinations:
            print(f"\n[!] ALERTA: {len(hallucinations)} tranzacții în DB care NU apar în OCR (Sospiciune Halucinație):")
            for h in hallucinations:
                print(f"  - {h[0]} | {h[1]} RON | {h[2]}")
        else:
            print("\n[+] REZULTAT: Toate tranzacțiile din DB sunt confirmate în textul OCR. 0 Halucinații.")

        if ocr_lines:
            print(f"\n[*] OBSERVAȚIE: {len(ocr_lines)} tranzacții în OCR care NU au ajuns în DB (Posibil ignorate/filtrare sume 0):")
            for o in ocr_lines[:5]:
                print(f"  - {o['date']} | {o['amount']} RON | {o['desc'][:50]}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_all_transactions(129)
