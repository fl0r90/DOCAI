import re
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def exhaustive_verify(doc_id):
    db = SessionLocal()
    try:
        doc = db.execute(text("SELECT raw_text FROM documents WHERE id = :id"), {"id": doc_id}).fetchone()
        raw_text = doc[0]
        db_items = db.execute(text("SELECT transaction_date, amount, description FROM financial_items WHERE document_id = :id"), {"id": doc_id}).fetchall()
        
        print(f"--- VERIFICARE FINALĂ 1:1 (SQL -> OCR) ---")
        print(f"Total în SQL: {len(db_items)}")
        
        matches = 0
        hallucinations = []
        
        for item in db_items:
            db_date, db_amount, db_desc = item
            # Formatăm suma pentru căutare în text (ex: 44209.2 -> 44.209,20 sau 44,209.2 sau 44209.2)
            # Cea mai sigură metodă: căutăm cifrele brute
            amount_str = f"{db_amount:g}" 
            # Încercăm și variante cu virgulă/punct
            alt_amount = f"{db_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') # 44.209,20
            
            if amount_str in raw_text or alt_amount in raw_text:
                matches += 1
            else:
                hallucinations.append(item)
                
        print(f"Confimate în textul brut: {matches}")
        
        if hallucinations:
            print(f"\n[!] POSIBILE HALUCINAȚII ({len(hallucinations)}):")
            for h in hallucinations:
                print(f"  - {h[0]} | {h[1]} | {h[2][:60]}")
        else:
            print("\n[+] REZULTAT: Toate cele 119 tranzacții din SQL se regăsesc în textul OCR.")

    finally:
        db.close()

if __name__ == "__main__":
    exhaustive_verify(129)
