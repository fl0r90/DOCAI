
import sys
import os
import json
sys.path.append('/app')

from core_engine.services.chat_service import AgenticInvestigator
from core_engine.database import SessionLocal
from core_engine.models import Document

def test_live_chat_behavior():
    print("=== [LIVE CHAT TEST] SIMULARE COMPORTAMENT NOU AGENT ===\n")
    
    with SessionLocal() as db:
        # Luam un case_id valid (cel care are factura Enel)
        doc = db.query(Document).filter(Document.filename.ilike("%Enel%")).first()
        if not doc:
            print("[!] Eroare: Nu am gasit documentul Enel pentru test.")
            return
        
        case_id = doc.case_id
        question = "Ce profit/rezultat a raportat OMV Petrom in T4/24 si ce achizitii noi au fost finalizate in decembrie 2024?"
        
        print(f"[USER]: {question}")
        print("-" * 50)
        
        agent = AgenticInvestigator(case_id, question)
        
        has_citations = False
        final_answer = ""
        
        # Simulam stream-ul de chat
        for chunk_json in agent.run():
            chunk = json.loads(chunk_json)
            c_type = chunk.get("type")
            c_data = chunk.get("data")
            
            if c_type == "step":
                print(f"\n[AGENT] {c_data}")
            elif c_type == "tool_call":
                print(f"  🛠️  APEL UNEALTA: {chunk.get('tool')}({chunk.get('params')})")
            elif c_type == "observation":
                obs = str(c_data)
                if "Thinking" in obs or "STRATEGIC PLAN" in obs:
                    print(f"  💭 {obs[:200]}...")
                else:
                    print(f"  👁️  OBSERVATIE: {obs[:100]}...")
            elif c_type == "final":
                final_answer = c_data
                if chunk.get("citations"):
                    has_citations = True
                    print(f"\n[CITATIONS FOUND]: {len(chunk.get('citations'))} surse.")

        print("\n" + "="*50)
        print("[FINAL RESPONSE FROM AGENT]:")
        print(final_answer)
        print("="*50)
        
        if has_citations:
            print("\n✅ TEST REUSIT: Agentul a gasit dovezi si a citat sursele.")
        else:
            print("\n❌ TEST ESUAT: Agentul nu a gasit citari (amnezie sau eroare de cautare).")

if __name__ == "__main__":
    test_live_chat_behavior()
