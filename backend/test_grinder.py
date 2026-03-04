from app.services.grinder import extract_forensic_data
from app.services.entity_resolver import save_entities_to_db
from app.database import SessionLocal
from app.models import Document

text_test = """
La data de 14.05.2023, numitul Popescu Ion, administrator la SC TEAPA SRL (CUI 12345678), 
a transferat suma de 150.000 RON în contul RO12INGB1234567890123456 deschis la ING Bank. 
Banii reprezintă contravaloarea facturii nr. 420 pentru servicii de consultanță fictive, 
facturată către SC FRAUDA SA.
"""

print("1. Trimit dosarul la Bestie...")
rezultat_json = extract_forensic_data(text_test)

if rezultat_json:
    print("\n2. Bestia a răspuns. Verific documentul în DB...")
    db = SessionLocal()
    try:
        # Verificăm dacă hash-ul există deja
        doc = db.query(Document).filter(Document.hash_sha256 == "fake_hash_420").first()
        
        if not doc:
            print("[+] Document nou. Îl salvez...")
            doc = Document(
                filename="test_frauda.pdf", 
                hash_sha256="fake_hash_420", 
                raw_text=text_test, 
                status="PROCESSED"
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
        else:
            print("[!] Documentul există deja. Folosesc ID-ul existent.")
            
        doc_id = doc.id
        # Acum salvăm entitățile extrase
        save_entities_to_db(rezultat_json, doc_id=doc_id)
        
    except Exception as e:
        print(f"Eroare la nivel de DB: {e}")
    finally:
        db.close()
else:
    print("A dat fail extracția.")
