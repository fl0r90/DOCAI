
import os
import json
import re
import requests
from core_engine.services.chat_service import AgenticInvestigator

CASE_ID = 5
QUERY = "Identifică plățile către LIDL și MEGAIMAGE din februarie 2026. Calculează suma lor totală și spune-mi ce procent reprezintă aceasta din soldul inițial al contului."

print(f"--- 🕵️ INVESTIGAȚIE FORENSICĂ (GEMMA) ---")
print(f"Întrebare: {QUERY}\n")

class GemmaForensicTest(AgenticInvestigator):
    def __init__(self, case_id, user_question):
        super().__init__(case_id, user_question)
        self.active_model = "gemma4:26b"

def test_run():
    agent = GemmaForensicTest(CASE_ID, QUERY)
    
    print(f"[MODEL ACTIV: {agent.active_model}]")
    
    for chunk_json in agent.run():
        data = json.loads(chunk_json)
        
        if data["type"] == "step":
            print(f"\n\n>>> {data['data'].upper()}")
        elif data["type"] == "tool_call":
            print(f"\n🛠️  [ACȚIUNE AGENT]: Apelare {data['tool']} cu parametrii: {data['params']}")
        elif data["type"] == "observation":
            print(f"👁️  [OBSERVAȚIE DATE]:\n{data['data']}")
        elif data["type"] == "chunk":
            # Printăm textul generat de model în timp real (gândirea lui)
            print(data['data'], end="", flush=True)
        elif data["type"] == "final":
            print(f"\n\n✅ [RAPORT FINAL INVESTIGATOR]:\n{data['data']}")

if __name__ == "__main__":
    test_run()
