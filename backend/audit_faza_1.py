
import sys
import os
sys.path.append('/app')
from core_engine.database import SessionLocal
from sqlalchemy import text

def audit_database_integrity():
    print("=== AUDIT FAZA 1: INTEGRITATE DB ===")
    with SessionLocal() as db:
        # 1. Verificare duplicate in tranzactii
        res = db.execute(text("""
            SELECT description, amount, transaction_date, COUNT(*) 
            FROM financial_items 
            GROUP BY description, amount, transaction_date 
            HAVING COUNT(*) > 1
        """)).fetchall()
        print(f"[!] Grupuri de tranzactii duplicate gasite: {len(res)}")
        for r in res[:5]:
            print(f"    - Duplicat: {r[0]} | {r[1]} RON | Count: {r[3]}")

        # 2. Verificare documente procesate vs neprocesate
        res = db.execute(text("SELECT status, COUNT(*) FROM documents GROUP BY status")).fetchall()
        print(f"[*] Status documente: {dict(res)}")

        # 3. Verificare distributie chunks per document
        res = db.execute(text("""
            SELECT d.filename, COUNT(c.id) 
            FROM documents d 
            LEFT JOIN document_chunks c ON d.id = c.document_id 
            GROUP BY d.filename
        """)).fetchall()
        print("[*] Distributie fragmente (Chunks):")
        for r in res:
            print(f"    - {r[0]}: {r[1]} chunks")

if __name__ == "__main__":
    audit_database_integrity()
