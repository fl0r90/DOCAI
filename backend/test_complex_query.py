
import os
import json
import re
import requests
from core_engine.services.chat_service import AgenticInvestigator

CASE_ID = 5
QUERY = "Identifică plățile către LIDL și MEGAIMAGE din februarie 2026. Calculează suma lor totală și spune-mi ce procent reprezintă aceasta din soldul inițial al contului."

print(f"--- FINAL COMPLEX INVESTIGATION ---")
print(f"Question: {QUERY}\n")

def test_run():
    # Folosim clasa de producție care acum are vLLM și Multi-Step configurat
    agent = AgenticInvestigator(CASE_ID, QUERY)
    
    print("[STARTING INVESTIGATION WITH DEEPSEEK-R1 (vLLM)]")
    
    full_answer = ""
    for chunk_json in agent.run():
        data = json.loads(chunk_json)
        
        if data["type"] == "step":
            print(f"\n>> {data['data']}")
        elif data["type"] == "tool_call":
            print(f"   [ACTION]: Calling {data['tool']} with: {data['params']}")
        elif data["type"] == "observation":
            print(f"   [OBSERVATION]: Received data from {data['data'][:50]}... (truncated)")
        elif data["type"] == "chunk":
            # Afișăm gândirea (thinking) dacă modelul o trimite, sau răspunsul parțial
            token = data['data']
            print(token, end="", flush=True)
        elif data["type"] == "final":
            full_answer = data['data']
            print(f"\n\n[FINAL INVESTIGATION REPORT]:\n{full_answer}")

if __name__ == "__main__":
    test_run()
