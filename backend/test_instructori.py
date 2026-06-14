import sys
import json
sys.path.append('/app')

from core_engine.services.chat_service import AgenticInvestigator

def test_live_chat_behavior():
    print("=== [LIVE CHAT TEST] INSTRUCTORI 50 PDF (Q8 KV CACHE) ===\n")
    
    case_id = 6 # Dosarul 'Test Cursuri' cu 50 PDF-uri
    question = "Identifică toți instructorii menționați în documente, asociază-i cu materiile/cursurile pe care le-au predat și calculează sau extrage orice date legate de sume sau ore pentru fiecare. Vreau un tablou complet al instructorilor."
    
    print(f"[USER]: {question}")
    print("-" * 50)
    
    agent = AgenticInvestigator(case_id, question)
    
    has_citations = False
    final_answer = ""
    
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
                print(f"  👁️  OBSERVATIE: {obs[:150]}...")
        elif c_type == "final":
            final_answer = c_data
            if chunk.get("citations"):
                has_citations = True
                print(f"\n[CITATIONS FOUND]: {len(chunk.get('citations'))} surse.")

    print("\n" + "="*50)
    print("[FINAL RESPONSE FROM AGENT]:")
    print(final_answer)
    print("="*50)

if __name__ == "__main__":
    test_live_chat_behavior()
