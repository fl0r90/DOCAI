import asyncio
import sys
import os
import json

# Adaugam backend-ul in sys.path ca sa vada core_engine
sys.path.append("/app")

from core_engine.services.grinder import extract_forensic_data

async def main():
    # Calea exacta gasita cu find in container
    pdf_path = "/app/uploads/extras de cont.pdf"
    
    print(f"[*] Incepem analiza Forensic (ASINC/TurboQuant+) pentru {pdf_path}...")
    
    # Pas 1: OCR - Citim PDF-ul
    from core_engine.services.ocr_service import process_document
    try:
        res_ocr = process_document(pdf_path)
        if isinstance(res_ocr, dict) and 'error' in res_ocr:
            print(f"[!] Eroare OCR: {res_ocr['error']}")
            return
            
        text_content = res_ocr.get('markdown', '')
    except Exception as e:
        print(f"[!] Eroare OCR Exception: {e}")
        return

    if not text_content:
        print("[!] ESEC: Nu am putut extrage text din document.")
        return

    print(f"[*] OCR Gata! {len(text_content)} caractere de analizat.")
    
    # Pas 2: Grinder Async (Gemma 4-E4B cu K=8, V=4)
    print("[*] Lansam motorul Gemma 4-E4B (TurboQuant+)...")
    res = await extract_forensic_data(text_content, "extras de cont.pdf", 777)
    
    print("\n" + "="*50)
    print(" REZULTATE PROCESARE FORENSIC (ALPHA v0.3.5)")
    print("="*50)
    print(f"TIP DOCUMENT: {res.get('doc_type')}")
    print(f"REZUMAT EXECUTIV: {res.get('summary')}")
    
    financials = res.get('metadata', {}).get('financial_data', [])
    print(f"TRANZACTII IDENTIFICATE: {len(financials)}")
    
    # Afisam top tranzactii
    if financials:
        print("\n--- TOP TRANZACTII ---")
        for idx, t in enumerate(financials[:5]):
            print(f"{idx+1}. {t.get('data')} | {t.get('descriere')} | {t.get('suma')} {t.get('valuta')}")

    # Salvam rezultatul
    with open("/app/audit_result_turbo.json", "w") as f:
        json.dump(res, f, indent=4)
    print("\n[*] Audit salvat in /app/audit_result_turbo.json")

if __name__ == "__main__":
    asyncio.run(main())
