
import os
import json
from core_engine.services.chat_service import query_investigator

def test_agent_directly():
    case_id = 5
    question = "Foloseste EXCLUSIV documentul ID 133 (OMV Petrom 2023). Gaseste Situatia Pozitiei Financiare si spune-mi valoarea exacta pentru 'Imobilizari corporale' la 31 decembrie 2023."
    print(f"[*] AGENT TEST START: {question}")
    
    try:
        result = query_investigator(case_id, question)
        print("\n" + "="*50)
        print("[+] AGENT RESPONSE:")
        print(result["answer"])
        print("="*50)
    except Exception as e:
        print(f"[!] TEST FAILED: {e}")

if __name__ == "__main__":
    test_agent_directly()
