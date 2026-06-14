import os
import sys

# Adaugăm calea către backend pentru a putea importa modulele
sys.path.append("/home/cfp-90/AI/V2/backend")

import json
import requests
from core_engine.services.grinder import _send_to_ollama
from core_engine.database import ForensicSessionLocal
from core_engine import models

def test_segment(doc_id, segment_idx):
    db = ForensicSessionLocal()
    try:
        # Preluăm chunk-ul
        chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc_id).order_by(models.DocumentChunk.id).offset(segment_idx).first()
        if not chunk:
            print(f"Segmentul {segment_idx} nu a fost găsit.")
            return

        print(f"Testing segment {segment_idx} (Chunk ID: {chunk.id})")
        
        system_msg = "Expert Forensic Data Extractor. Extract objective facts as structured JSON."
        user_msg = f"""Mission: Identify all financial transactions, entities, and provide a brief segment summary.
JSON SCHEMA:
{{
    "sinteza_segment": "Segment summary (max 2 sentences)",
    "entitati": [{{"tip_entitate": "Persoana|Firma|IBAN|Telefon", "valoare": "Value", "rol": "Context"}}],
    "tranzactii": [{{
        "data": "YYYY-MM-DD", 
        "descriere": "Raw description", 
        "suma": 0.0, 
        "valuta": "RON/EUR",
        "cui_sursa": "Source TAX ID",
        "iban_sursa": "Source IBAN",
        "cui_destinatie": "Destination TAX ID",
        "iban_destinatie": "Destination IBAN"
    }}]
}}
Input Text:
{chunk.content}"""

        prompt = f"### System:\n{system_msg}\n\n### User:\n{user_msg}\n\n### Assistant:\n"
        
        # Folosim qwen2.5-coder:7b care e setat pentru tabele în config (sau vedem ce e activ)
        model = "qwen2.5-coder:7b" 
        
        print(f"Calling Ollama with model {model}...")
        
        # Trimitem manual să vedem răspunsul brut dacă eșuează JSON
        payload = {
            "model": model, 
            "prompt": prompt, 
            "stream": False, 
            "options": {"temperature": 0.01},
            "format": "json"
        }
        
        OLLAMA_URL = "http://llm:11434" # Presupunem că e mapat sau rulăm în container
        try:
            res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=1200)
            print(f"Status: {res.status_code}")
            if res.status_code == 200:
                response_json = res.json()
                raw_response = response_json.get("response", "")
                print("RAW RESPONSE:")
                print(raw_response)
                
                try:
                    parsed = json.loads(raw_response)
                    print("PARSED SUCCESSFUL")
                except Exception as e:
                    print(f"PARSED FAILED: {e}")
            else:
                print(f"Error: {res.text}")
        except Exception as e:
            print(f"Request Exception: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    test_segment(133, 65)
