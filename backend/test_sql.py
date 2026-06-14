
import os
import requests
import json
import re

OLLAMA_URL = "http://llm:11434"

def _extract_json(text):
    try:
        if not text: return None
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        json_match = re.search(r'```json\s*(.*?)\s*```', clean, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{.*\}', clean, re.DOTALL)
        if json_match:
            json_str = json_match.group(1) if "```json" in clean else json_match.group(0)
            return json.loads(json_str)
        return None
    except: return None

def test_sql_generation(question, case_id):
    active_model = "qwen3.5:9b"
    prompt = f"""### System:
Expert PostgreSQL Developer.
Misiune: Generare SQL pentru baza de date Forensic.
TABELE:
- documents (id, filename, case_id)
- financial_items (id, document_id, description, amount, currency, transaction_date, transaction_type, cui_source, iban_source)

REGULI CRITICE:
1. Folosește DOAR documentele din case_id = {case_id}.
2. Pentru ALIAS-uri folosește GHILIMELE DUBLE (ex: AS "Total") sau nimic. NU folosi ghilimele simple pentru coloane.
3. Dacă întrebarea cere procente sau rectificări, caută în descrierile financial_items.
4. Returnează DOAR codul SQL, fără explicații.

### User:
ÎNTREBARE: {question}
### Assistant:
"""
    try:
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": active_model, "prompt": prompt, "stream": False, "format": "json"
        }, timeout=60)
        resp = res.json().get("response", "{}")
        print(f"[*] Raw LLM Response: {resp}")
        sql_json = _extract_json(resp)
        return sql_json.get("sql", "").strip() if sql_json else ""
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    q = "Conform situației consolidate a veniturilor, care este diferența dintre 'Venituri din vânzări' și 'Total venituri din vânzări și alte venituri' pentru anul 2023?"
    sql = test_sql_generation(q, 5)
    print(f"\n[*] GENERATED SQL: {sql}")
