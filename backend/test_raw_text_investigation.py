
import os
import json
import re
import requests
from core_engine.services.chat_service import AgenticInvestigator

CASE_ID = 5
QUERY = "Analizează EXCLUSIV textul brut al extrasului de cont. Cât a fost plata la LIDL pe 16 februarie 2026? Identifică suma corectă din coloana de Debit, nu din coloana de Sold."

print(f"--- 🔍 TEST INVESTIGAȚIE TEXT BRUT (OCR) ---")
print(f"Întrebare: {QUERY}\n")

class RawTextInvestigator(AgenticInvestigator):
    def __init__(self, case_id, user_question):
        super().__init__(case_id, user_question)
        self.active_model = "gemma4:26b"

def test_run():
    agent = RawTextInvestigator(CASE_ID, QUERY)
    
    # Dezactivăm injecția SQL pentru a forța modelul să caute în text
    agent.injected_evidence = "DO NOT USE SQL DATA. USE SEARCH_TEXT ONLY."
    
    for chunk_json in agent.run():
        data = json.loads(chunk_json)
        
        if data["type"] == "step":
            print(f"\n>>> {data['data'].upper()}")
        elif data["type"] == "tool_call":
            print(f"\n🛠️  [ACȚIUNE]: {data['tool']}({data['params']})")
        elif data["type"] == "observation":
            # Arătăm o parte din textul brut care i-a venit
            print(f"👁️  [DATE BRUTE PRIMITE]:\n{data['data'][:500]}...")
        elif data["type"] == "chunk":
            print(data['data'], end="", flush=True)
        elif data["type"] == "final":
            print(f"\n\n✅ [RAPORT FINAL]:\n{data['data']}")

if __name__ == "__main__":
    test_run()
