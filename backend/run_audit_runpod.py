
import sys
import os
import json
import time
import subprocess
from sqlalchemy import text

# Adaugam path-ul pentru core_engine
sys.path.append('/workspace/backend')

from core_engine.database import SessionLocal
from core_engine.services.grinder import extract_forensic_data

def run_ocr_isolated(file_path):
    print(f"[*] Lansare OCR izolat pe CPU...")
    # Rulăm un script separat care nu vede placa video
    cmd = [
        "python3", "-c", 
        f"import os, json; os.environ['CUDA_VISIBLE_DEVICES'] = ''; from core_engine.services.ocr_service import process_document; print(json.dumps(process_document('{file_path}')))"
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "" 
    
    result = subprocess.check_output(cmd, env=env)
    return json.loads(result)

def run_runpod_audit_final():
    print("=== AUDIT FORENSIC SUPREM (RTX 5090 + GEMMA 4) ===")
    
    file_path = "/workspace/uploads/extras de cont.pdf"
    filename = "extras de cont.pdf"
    
    with SessionLocal() as db:
        res = db.execute(text("INSERT INTO documents (filename, status, case_id) VALUES (:f, :s, :c) RETURNING id"), 
                         {"f": filename, "s": "PROCESSING", "c": 1})
        doc_id = res.fetchone()[0]
        db.commit()

        start_time = time.time()
        try:
            ocr_result = run_ocr_isolated(file_path)
            raw_text = ocr_result.get("markdown", "")
            print(f"[+] OCR Finalizat pe CPU. Timp: {time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"[!] EROARE OCR: {e}")
            return

        print(f"[*] Lansare Extracție AI pe RTX 5090...")
        start_time = time.time()
        # Grinder folosește modelul setat în DB (Gemma 4:e4b)
        res = extract_forensic_data(raw_text, filename, doc_id)
        print(f"[+] Extracție finalizată în {time.time() - start_time:.2f} secunde.")

        transactions = res.get("metadata", {}).get("financial_data", [])
        print(f"\n[*] Audit Finalizat. Tranzacții găsite: {len(transactions)}")
        
        for t in transactions:
            try:
                # Verificăm atât 'suma' (din AI) cât și 'amount' (după normalizare)
                val = float(t.get("suma") or t.get("amount") or 0)
                if abs(val - 10500.0) < 0.1:
                    print(f"[REUȘITĂ!] Suma de 10500 RON a fost identificată corect.")
                    print(f"Detalii: {t.get('descriere') or t.get('description')}")
                    return
            except: pass
        
        print("[!] Suma de 10500 lei nu a fost găsită. Verifică datele extrase.")

if __name__ == "__main__":
    run_runpod_audit_final()
