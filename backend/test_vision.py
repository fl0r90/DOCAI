
import os
import requests
import json

OLLAMA_URL = "http://llm:11434"

def test_direct_read(active_model):
    # Aceasta este exact bucata din baza de date (Fragmentul 94)
    evidence = """
[SURSA PROBA: omv-petrom-group-2023-annual-report...pdf]
|                                                                       |   Note | 31 decembrie 2023   | 31 decembrie 2022 1   |
|-----------------------------------------------------------------------|--------|---------------------|-----------------------|
| ACTIVE                                                                |        |                     |                       |
| Imobilizari necorporale                                               |      7 | 655,74              | 3.015,67              |
| Imobilizari corporale                                                 |      8 | 30.099,20           | 24.751,07             |
| Investitii in entitati asociate                                       |      9 | 48,11               | 40,83                 |
| Alte active financiare                                                |     10 | 2.077,17            | 2.047,46              |
"""
    
    prompt = f"""### System:
You are a SENIOR FORENSIC INVESTIGATOR.
Rule: Use ONLY the provided evidence.

### User:
DATE ȘI PROBE RELEVANTE:
{evidence}

ÎNTREBARE: Care este valoarea exacta a 'Imobilizari corporale' la 31 decembrie 2023?
### Assistant:
"""
    
    try:
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": active_model, "prompt": prompt, "stream": False
        }, timeout=60)
        return res.json().get("response", "")
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    # Testăm cu ambele modele dacă sunt disponibile
    for model in ["qwen3.5:9b", "mistral-nemo:12b"]:
        print(f"\n[*] Testing model: {model}")
        print(f"[*] Response: {test_direct_read(model)}")
