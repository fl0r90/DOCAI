
import os
import json
import re
import requests
from core_engine.services.chat_service import AgenticInvestigator

CASE_ID = 5
QUERY = "Identifică plățile către LIDL și MEGAIMAGE din februarie 2026. Calculează suma lor totală și spune-mi ce procent reprezintă aceasta din soldul inițial al contului."

print(f"--- OLLAMA INVESTIGATION TEST ---")
print(f"Question: {QUERY}\n")

class OllamaTestInvestigator(AgenticInvestigator):
    def __init__(self, case_id, user_question):
        super().__init__(case_id, user_question)
        self.active_model = "gemma4:26b" # Forțăm gemma4 din Ollama

def test_run():
    agent = OllamaTestInvestigator(CASE_ID, QUERY)
    
    print(f"[USING MODEL: {agent.active_model}]")
    
    full_answer = ""
    for chunk_json in agent.run():
        data = json.loads(chunk_json)
        
        if data["type"] == "step":
            print(f"\n>> {data['data']}")
        elif data["type"] == "tool_call":
            print(f"   [ACTION]: Calling {data['tool']} with: {data['params']}")
        elif data["type"] == "observation":
            print(f"   [OBSERVATION]: Received {len(data['data'])} chars of data.")
        elif data["type"] == "chunk":
            print(data['data'], end="", flush=True)
        elif data["type"] == "final":
            full_answer = data['data']
            print(f"\n\n[FINAL REPORT]:\n{full_answer}")

if __name__ == "__main__":
    test_run()
