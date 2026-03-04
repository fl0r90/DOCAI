import os
import sys

# Setăm cache-ul înainte de orice import care ar putea inițializa HF
HF_HOME = os.getenv("HF_HOME", "/app/ocr_cache/huggingface")
os.environ["HF_HOME"] = HF_HOME
os.makedirs(HF_HOME, exist_ok=True)

from docling.document_converter import DocumentConverter

def preload():
    print(f"[*] Începe pre-încărcarea modelelor OCR în {HF_HOME}...")
    
    try:
        # Inițializarea converter-ului forțează download-ul modelelor implicite
        # Docling va folosi HF_HOME setat mai sus
        converter = DocumentConverter()
        print("[+] Modelele Docling/HuggingFace au fost încărcate cu succes.")
        
    except Exception as e:
        print(f"[-] Eroare la pre-încărcare: {e}")
        sys.exit(1)

if __name__ == "__main__":
    preload()
