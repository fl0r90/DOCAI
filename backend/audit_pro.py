
import sys
import os
import json
import requests
sys.path.append('/app')

from core_engine.database import SessionLocal
from core_engine.models import DocumentChunk, Document
from core_engine.services.chat_service import AgenticInvestigator
from sqlalchemy import text

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

def generate_question(chunk_content):
    prompt = f"""
    ESTI UN AUDITOR FORENSIC. Pe baza fragmentului de mai jos dintr-un document, genereaza o singura intrebare FOARTE SPECIFICA.
    Intrebarea trebuie sa se refere la date concrete (nume, sume, date, termeni tehnici) prezente in text.
    Fragment: \"\"\"{chunk_content}\"\"\"
    
    REGULA: Returneaza DOAR intrebarea, fara explicatii sau introduceri.
    """
    try:
        payload = {
            "model": "gemma4:e4b",
            "prompt": prompt,
            "stream": False
        }
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"[!] Errare generare: {e}")
        return None

def run_detailed_audit():
    print(f"=== [PRO AUDITOR] DEBUG MODE: INVESTIGATIE DETALIATA ===\n")
    
    with SessionLocal() as db:
        # Luam un chunk care stim ca are continut (cel de la Testul 1 anterior sau unul similar)
        chunk = db.query(DocumentChunk).filter(DocumentChunk.content.ilike("%disclaimer%")).first()
        if not chunk:
            chunk = db.query(DocumentChunk).order_by(text("RANDOM()")).first()
            
        doc = db.query(Document).filter(Document.id == chunk.document_id).first()
        
        print(f"[*] DOCUMENT SURSA: {doc.filename}")
        print(f"[*] CONTINUT CHUNK (Scurtat): {chunk.content[:300]}...\n")
        
        question = generate_question(chunk.content[:2000])
        print(f"[?] INTREBARE GENERATA: {question}\n")
        
        print(f"--- INCEPUT LOG INVESTIGATIE ---")
        agent = AgenticInvestigator(doc.case_id, question)
        
        full_answer = ""
        for chunk_json in agent.run():
            step_data = json.loads(chunk_json)
            t = step_data.get("type")
            d = step_data.get("data")
            
            if t == "step":
                print(f"\n[STEP] {d}")
            elif t == "observation":
                # Printam doar inceputul observatiei daca e prea lunga
                obs_preview = str(d)[:500] + "..." if len(str(d)) > 500 else str(d)
                print(f"[OBSERVATION] {obs_preview}")
            elif t == "tool_call":
                print(f"[TOOL CALL] {step_data.get('tool')}({step_data.get('params')})")
            elif t == "final":
                full_answer = d
                print(f"\n[FINAL RESPONSE]\n{full_answer}")
                print(f"\n[CITATIONS] {step_data.get('citations')}")

        # Verificare succes
        cited_docs = [c.get('filename') for c in agent.citations]
        if doc.filename in cited_docs:
            print(f"\n✅ REUSITA: Documentul corect a fost citat.")
        else:
            print(f"\n❌ ESEC: Documentul NU a fost gasit in citari.")

if __name__ == "__main__":
    run_detailed_audit()
