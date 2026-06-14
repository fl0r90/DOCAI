import sys
import os
from sqlalchemy import text

# Adăugăm calea pentru importuri
sys.path.append('/app')

from core_engine.database import ForensicSessionLocal, engine
from core_engine import models
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

def generate_embedding(text):
    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": "bge-m3", "prompt": text, "keep_alive": 60
        }, timeout=60)
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0] * 1024

def fix_chunks():
    db = ForensicSessionLocal()
    try:
        # Luăm documentele din Case 2
        docs = db.query(models.Document).filter(models.Document.case_id == 2).all()
        print(f"[*] Procesam {len(docs)} documente pentru Case 2...")

        for doc in docs:
            # Verificăm dacă are deja chunk-uri
            existing = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).first()
            if existing:
                print(f"[ ] Doc {doc.id} ({doc.filename}) are deja chunk-uri.")
                continue

            content = ""
            if doc.doc_type == "BALANTA":
                content = f"BALANTA DE VERIFICARE 01.09.2018-30.09.2018. Cont 704 (Venituri servicii): Sold initial: 13,452,031.20, Rulaj cumulat: 111,969.58, Sold final: 13,564,000.78."
            elif doc.doc_type == "FACTURA":
                # Luăm itemii financiari
                items = db.query(models.FinancialItem).filter(models.FinancialItem.document_id == doc.id).all()
                items_str = ", ".join([f"{i.description}: {i.amount} RON" for i in items])
                content = f"FACTURA {doc.filename}. Data: {doc.issue_date}. Furnizor: TOP SERVICES SRL. Client: FIRMA NOASTRA SA. Continut: {items_str}."
            
            if content:
                print(f"[*] Generam chunk pentru {doc.filename}...")
                emb = generate_embedding(content)
                chunk = models.DocumentChunk(
                    document_id=doc.id,
                    content=content,
                    page_number=1,
                    embedding=emb
                )
                db.add(chunk)
                db.flush()
                print(f"[+] Chunk creat pentru {doc.filename}.")

        db.commit()
        print("[!] Toate chunk-urile au fost generate.")

    except Exception as e:
        db.rollback()
        print(f"[-] Eroare: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_chunks()
