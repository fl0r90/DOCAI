
import os
import sys
import json

# Add backend to path
sys.path.append("/app")

from core_engine.services.chat_service import query_investigator

def verify_user_question():
    case_id = 5
    question = "Identifică tranzacțiile către ACVILE TECH din februarie 2026. Compară extrasul de cont cu factura acestora și calculează suma totală. Există vreo discrepanță între factură și plata reală?"
    
    print(f"[*] VERIFYING AGENT RESPONSE FOR CASE {case_id}...")
    print(f"[*] Question: {question}")
    
    try:
        # We call the investigator directly to see the final answer
        result = query_investigator(case_id, question)
        
        print("\n" + "="*50)
        print("AGENT ANSWER:")
        print("="*50)
        print(result.get("answer", "No answer generated."))
        print("="*50)
        
        print("\nCITATIONS FOUND:", len(result.get("citations", [])))
        for c in result.get("citations", []):
            print(f"- Doc ID: {c.get('doc_id')} | Page: {c.get('page')}")
            
    except Exception as e:
        print(f"[!] VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_user_question()
