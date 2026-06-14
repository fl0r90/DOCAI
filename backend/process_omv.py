import os
import sys

# Adaugam backend in path
sys.path.append('/app/backend')

from core_engine.services.ocr_service import process_document

def process_omv():
    file_path = "/app/uploads/omv-petrom-group-2023-annual-report-including-consolidated-financial-statements.pdf"
    if not os.path.exists(file_path):
        print(f"[-] Fisierul nu exista la {file_path}")
        return

    print(f"[*] Incepem OCR pentru: {file_path}")
    result = process_document(file_path)
    
    if "error" in result:
        print(f"[!] Eroare: {result['error']}")
    else:
        markdown = result.get("markdown", "")
        print(f"[+] OCR Finalizat. Lungime text: {len(markdown)}")
        
        # Salvam rezultatul intr-un fisier temporar pentru a-l citi
        with open("/app/temp_omv_ocr.md", "w") as f:
            f.write(markdown)
        print("[+] Rezultat salvat in /app/temp_omv_ocr.md")

if __name__ == "__main__":
    process_omv()
