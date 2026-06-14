import sys
import json
sys.path.append('/app')

from core_engine.services.chat_service import AgenticInvestigator

def test_live_chat_intersectie():
    print("=== [LIVE CHAT TEST] INTERSECTIE PARTICIPANTI 50 PDF ===\n")
    
    case_id = 6 # Dosarul 'Test Cursuri'
    question = "Află lista tuturor cursanților care au fost prezenți la cursurile predate de TOȚI cei trei instructori: Gheorghe Ionescu, Vasile Georgescu și Elena Vasilescu. Folosește SEARCH_STRUCTURED_DATA cu limit=100 pentru fiecare instructor ca să extragi listele complete de prezență, apoi intersectează-le și prezintă cursanții comuni cu dovezile aferente."
    
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
    test_live_chat_intersectie()
