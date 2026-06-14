
import json
import asyncio
import sys
import os

# Adăugăm calea către backend
sys.path.append("/home/cfp-90/AI/V2/backend")

# Mock environment pentru a rula local
os.environ["OLLAMA_URL"] = "http://llm:11434" # Folosim numele din rețeaua docker
os.environ["FORENSIC_DATABASE_URL"] = "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db"

from core_engine.services.chat_service import AgenticInvestigator

async def test_agent_loop():
    case_id = 5 # ID-ul cazului din loguri
    question = "Care a fost profitul net CCA excluzând elementele speciale în 2024 și ce pierderi au fost raportate la segmentul Corporativ?"
    
    print(f"\n[USER]: {question}\n")
    agent = AgenticInvestigator(case_id, question)
    
    # Rulăm agentul și afișăm pașii de gândire și apelurile de unelte
    async for step_json in agent.run_async(): # Folosim o variantă async dacă e cazul sau transformăm generatorul
        data = json.loads(step_json)
        
        if data["type"] == "status":
            print(f"[*] {data['data']}")
        elif data["type"] == "step":
            print(f"\n--- {data['data']} ---")
        elif data["type"] == "tool_call":
            print(f"[TOOL CALL]: {data['tool']}({data['params']})")
        elif data["type"] == "observation":
            print(f"[OBSERVATION]: {data['data'][:500]}...")
        elif data["type"] == "final":
            print(f"\n[AGENT FINAL ANSWER]:\n{data['data']}")

# Deoarece chat_service.py este sincron (yield), îl rulăm direct
def run_sync_test():
    case_id = 5
    question = """Efectuează un audit detaliat al tranzacțiilor SC ALPHA SRL pe baza documentelor disponibile:

1. Analiză Contractuală: Identifică relația cu 'BETA SOLUTIONS SRL'. Verifică dacă valoarea din contractul nr. 2026/01 coincide cu factura emisă ulterior și cu plata efectuată în extrasul de cont.
2. Urmărirea Fluxului (Money Trail): Cine este beneficiarul final al plății pentru factura 101? Este acesta contul oficial al companiei prestatoare menționat în contract?
3. Conflict de Interese: Analizează structura de management a firmelor 'ALPHA SRL' și 'GAMMA TRADING'. Există elemente comune între administratorii sau asociații acestora?
4. Filtrare Probe Relevante: Menționează care din documentele procesate nu au nicio legătură cu activitatea economică a ALPHA SRL.

Respectă formatul forensic [FACTS], [ANALYSIS], [CONCLUSION] și evaluează încrederea [CONFIDENCE]."""
    
    print(f"\n[USER]: {question}\n")
    agent = AgenticInvestigator(case_id, question)
    
    for step_json in agent.run():
        data = json.loads(step_json)
        if data["type"] == "status":
            print(f"[*] {data['data']}")
        elif data["type"] == "step":
            print(f"\n--- {data['data']} ---")
        elif data["type"] == "tool_call":
            print(f"[TOOL CALL]: {data['tool']}({data['params']})")
        elif data["type"] == "observation":
            print(f"[OBSERVATION]: {data['data'][:500]}...")
        elif data["type"] == "final":
            print(f"\n[AGENT FINAL ANSWER]:\n{data['data']}")

if __name__ == "__main__":
    run_sync_test()
